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

    [BPS 계산 방식]
    KR 종목: yfinance quarterly_balance_sheet에서 BPS 직접 계산
             (Stockholders Equity / Ordinary Shares Number)
    US 종목: yfinance tk.info.bookValue 기반 근사

    보정 방침:
    1. pbr_min_value에 보수적 가중치(CONSERVATIVE_FACTOR=1.2) 적용
    2. StatsUpdater(매주 토요일)가 최신 장부가치로 점진적 보정
    """
    try:
        pbr_series = None

        # KR 종목: FinanceDataReader 우선 시도
        if ticker.endswith(".KS") or ticker.endswith(".KQ"):
            pbr_series = _get_pbr_from_fdr(ticker, start, end)

        # US 종목 또는 FDR 실패 시: yfinance bookValue 기반 근사
        if pbr_series is None or pbr_series.empty:
            pbr_series = _get_pbr_from_yfinance(ticker, start, end)

        if pbr_series is None or pbr_series.empty:
            logger.warning(f"pbr_data_unavailable ticker={ticker}")
            return None

        raw_min = float(pbr_series.min())
        conservative_min = round(raw_min * CONSERVATIVE_FACTOR, 4)

        logger.info(
            f"pbr_stats_generated ticker={ticker} "
            f"raw_min={round(raw_min, 4)} "
            f"conservative_min={conservative_min} "
            f"factor={CONSERVATIVE_FACTOR}"
        )

        return StockStatsRecord(
            ticker=ticker,
            stat_type="PBR_STATS",
            pbr_min_value=conservative_min,
            pbr_max_value=round(float(pbr_series.max()), 4),
            pbr_median_value=round(float(pbr_series.median()), 4),
            years_of_data=SEED_YEARS,
            updated_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"pbr_stats_generation_failed ticker={ticker} error={str(e)}")
        return None


def _get_pbr_from_fdr(ticker: str, start: str, end: str):
    """
    yfinance balance sheet에서 BPS를 직접 계산하여 PBR 시계열 생성.
    KR 종목은 priceToBook/bookValue가 None이므로 이 방식을 사용.
    BPS = Stockholders Equity / Ordinary Shares Number
    PBR = Close / BPS
    """
    try:
        tk = yf.Ticker(ticker)
        bs = tk.quarterly_balance_sheet
        if bs is None or bs.empty:
            return None

        # 최신 분기 재무제표에서 BPS 계산
        if "Stockholders Equity" not in bs.index or "Ordinary Shares Number" not in bs.index:
            return None

        equity = bs.loc["Stockholders Equity"].iloc[0]
        shares = bs.loc["Ordinary Shares Number"].iloc[0]
        if not equity or not shares or float(shares) <= 0:
            return None

        bps = float(equity) / float(shares)
        if bps <= 0:
            return None

        # 히스토리컬 주가 로드
        hist = tk.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            return None

        pbr_series = (hist["Close"] / bps).dropna().round(4)
        logger.info(f"pbr_from_balance_sheet ticker={ticker} bps={bps:.0f} latest_pbr={pbr_series.iloc[-1]:.4f}")
        return pbr_series
    except Exception as e:
        logger.warning(f"fdr_pbr_stats_failed ticker={ticker} error={str(e)}")
        return None


def _get_pbr_from_yfinance(ticker: str, start: str, end: str):
    """yfinance bookValue 기반 PBR 시계열 근사 (US 종목 전용)"""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            return None
        info = tk.info
        book_value = info.get("bookValue")
        if not book_value or float(book_value) <= 0:
            return None
        pbr_series = (hist["Close"] / float(book_value)).dropna().round(4)
        return pbr_series
    except Exception as e:
        logger.warning(f"yf_pbr_stats_failed ticker={ticker} error={str(e)}")
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
