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


def generate_pbr_stats(ticker: str, start: str, end: str) -> StockStatsRecord | None:
    """
    5~10년 PBR 히스토리컬 데이터로 Min/Max/Median 계산.

    [BPS 계산 방식]
    분기별 balance sheet BPS를 일별로 forward-fill하여 시계열 PBR 계산.
    단일 현재 BPS 사용 시 과거 PBR이 비현실적으로 낮아지는 문제 해결.

    [임계값 적용 원칙]
    StockStatsTable에는 순수한 역사적 최저 PBR 원본 값만 저장.
    보수적 임계값 평가는 shared/scoring.py의 pbr_min_value * 1.1 로직에서만 단독 적용.
    """
    try:
        import pandas as pd
        tk = yf.Ticker(ticker)
        hist = tk.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            logger.warning(f"pbr_no_history ticker={ticker}")
            return None

        pbr_series = _calc_historical_pbr(tk, hist)
        if pbr_series is None or pbr_series.empty:
            logger.warning(f"pbr_data_unavailable ticker={ticker}")
            return None

        raw_min = float(pbr_series.min())
        logger.info(f"pbr_stats_generated ticker={ticker} pbr_min={round(raw_min, 4)} pbr_median={round(float(pbr_series.median()), 4)}")

        return StockStatsRecord(
            ticker=ticker,
            stat_type="PBR_STATS",
            pbr_min_value=round(raw_min, 4),
            pbr_max_value=round(float(pbr_series.max()), 4),
            pbr_median_value=round(float(pbr_series.median()), 4),
            years_of_data=SEED_YEARS,
            updated_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"pbr_stats_generation_failed ticker={ticker} error={str(e)}")
        return None


def _calc_historical_pbr(tk, hist):
    """
    연간+분기 balance sheet BPS를 일별 forward-fill하여 시계열 PBR 계산.
    - 연간(4년) + 분기(4~5분기) 합산으로 커버리지 확대
    - timezone-aware hist index를 tz-naive로 정규화하여 KR 종목 호환
    - fallback: tk.info.bookValue (단일값)
    """
    import pandas as pd

    def _bps_from_bs(bs):
        if bs is None or bs.empty:
            return None
        if "Stockholders Equity" not in bs.index or "Ordinary Shares Number" not in bs.index:
            return None
        eq = bs.loc["Stockholders Equity"].dropna()
        sh = bs.loc["Ordinary Shares Number"].dropna()
        common = eq.index.intersection(sh.index)
        s = pd.Series(
            {d: float(eq[d]) / float(sh[d]) for d in common if float(sh[d]) > 0},
            dtype=float,
        ).sort_index()
        return s[s > 0] if not s.empty else None

    # hist index를 tz-naive date로 정규화 (KR 종목은 Asia/Seoul tz-aware)
    hist_norm = hist.copy()
    if hist_norm.index.tz is not None:
        hist_norm.index = hist_norm.index.normalize().tz_localize(None)

    try:
        bps_annual = _bps_from_bs(tk.balance_sheet)
        bps_quarterly = _bps_from_bs(tk.quarterly_balance_sheet)
        parts = [s for s in [bps_annual, bps_quarterly] if s is not None]
        if parts:
            bps_combined = pd.concat(parts).sort_index()
            bps_combined = bps_combined[~bps_combined.index.duplicated(keep="last")]
            bps_daily = (
                bps_combined
                .reindex(bps_combined.index.union(hist_norm.index))
                .sort_index()
                .ffill()
                .reindex(hist_norm.index)
            )
            valid = bps_daily.dropna()
            if len(valid) >= len(hist_norm) * 0.3:
                pbr = (hist_norm["Close"] / bps_daily).dropna().round(4)
                result = pbr[pbr > 0]
                if not result.empty:
                    return result
    except Exception:
        pass

    try:
        book_value = tk.info.get("bookValue")
        if book_value and float(book_value) > 0:
            pbr = (hist_norm["Close"] / float(book_value)).dropna().round(4)
            return pbr[pbr > 0]
    except Exception:
        pass
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
