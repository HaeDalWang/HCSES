"""
StockStatsTable Seed Data 생성 및 DynamoDB 마이그레이션
TC-06: Unit 2 실행 전 필수 실행
"""
import logging
import os
import random
import time
from datetime import datetime, timedelta

import numpy as np
import yfinance as yf

from src.shared import dynamodb_client as db
from src.shared.models import StockStatsRecord

logger = logging.getLogger(__name__)

STOCK_STATS_TABLE = os.environ.get("STOCK_STATS_TABLE", "hcses-stock-stats")
SEED_YEARS = int(os.environ.get("STATS_YEARS", "7"))
CONSERVATIVE_FACTOR = 1.2  # pbr_min 보수적 상향 조정 계수 (현재 장부가치 근사 오차 보정)


def generate_pbr_stats(ticker: str, start: str, end: str) -> StockStatsRecord | None:
    """
    5~10년 PBR 히스토리컬 데이터로 Min/Max/Median 계산.

    [설계 한계 및 보정 방침]
    현재 yfinance tk.info.get("bookValue")는 현재 시점의 단일 장부가치만 제공합니다.
    기업의 장부가치는 매년 변동하므로, 10년 전 주가를 현재 장부가치로 나눈 PBR은
    실제 과거 PBR과 오차가 발생할 수 있습니다.

    보정 방침:
    1. pbr_min_value에 보수적 가중치(CONSERVATIVE_FACTOR=1.2) 적용:
       실제 과거 최저 PBR보다 20% 높게 설정하여 과도한 저평가 판단 방지.
    2. StatsUpdater(매주 토요일)가 최신 장부가치로 점진적 보정.
    3. 향후 개선: yfinance quarterly_financials에서 연도별 BPS 추출 권장.
    """
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            return None

        info = tk.info
        book_value = info.get("bookValue")
        if not book_value or float(book_value) <= 0:
            logger.warning(f"book_value_missing ticker={ticker}")
            return None

        pbr_series = (hist["Close"] / float(book_value)).dropna()
        if pbr_series.empty:
            return None

        raw_min = float(pbr_series.min())
        # 보수적 가중치 적용: 현재 장부가치 기반 계산의 한계 보정
        conservative_min = round(raw_min * CONSERVATIVE_FACTOR, 4)

        logger.info(
            f"pbr_stats_generated ticker={ticker} "
            f"raw_min={round(raw_min, 4)} "
            f"conservative_min={conservative_min} "
            f"factor={CONSERVATIVE_FACTOR} "
            f"note=current_book_value_approximation"
        )

        return StockStatsRecord(
            ticker=ticker,
            stat_type="PBR_STATS",
            pbr_min_value=conservative_min,          # 보수적 가중치 적용
            pbr_max_value=round(float(pbr_series.max()), 4),
            pbr_median_value=round(float(pbr_series.median()), 4),
            years_of_data=SEED_YEARS,
            updated_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"pbr_stats_generation_failed ticker={ticker} error={str(e)}")
        return None


def generate_and_migrate_seed(tickers: list[str], start: str, end: str) -> None:
    """Seed Data 생성 후 DynamoDB StockStatsTable에 업로드"""
    logger.info(f"seed_migration_start ticker_count={len(tickers)}")
    success, failed = [], []

    for ticker in tickers:
        stats = generate_pbr_stats(ticker, start, end)
        if stats:
            db.save_stock_stats(stats, STOCK_STATS_TABLE)
            success.append(ticker)
            logger.info(f"seed_migrated ticker={ticker} "
                        f"pbr_min={stats.pbr_min_value} "
                        f"pbr_median={stats.pbr_median_value} "
                        f"pbr_max={stats.pbr_max_value}")
        else:
            failed.append(ticker)
        time.sleep(random.uniform(1, 3))

    logger.info(f"seed_migration_complete success={success} failed={failed}")
    print(f"\n[Seed 마이그레이션] 성공: {len(success)}개 / 실패: {len(failed)}개")
    if failed:
        print(f"  실패 종목: {failed}")
