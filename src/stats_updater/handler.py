"""
StatsUpdater Lambda 핸들러
매주 토요일 PBR Min/Max/Median 재계산 → StockStatsTable 업데이트
"""
import json
import logging
import os
import random
import time
from datetime import datetime, date, timedelta
from typing import Optional

import numpy as np
import yfinance as yf

from src.shared import dynamodb_client as db
from src.shared.models import StockStatsRecord
from src.data_collector.handler import TICKER_LIST

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

STOCK_STATS_TABLE = os.environ.get("STOCK_STATS_TABLE", "hcses-stock-stats")
STATS_YEARS = int(os.environ.get("STATS_YEARS", "7"))  # 5~10년, 기본 7년


def _log(level: str, message: str, **kwargs) -> None:
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        json.dumps({"timestamp": datetime.utcnow().isoformat(), "level": level,
                    "message": message, **kwargs})
    )


def recalculate_pbr_stats(ticker: str) -> Optional[StockStatsRecord]:
    """
    최근 N년 PBR Min/Max/Median 계산.
    분기별 balance sheet BPS를 일별로 보간하여 시계열 PBR 계산.
    단일 현재 BPS 사용 시 과거 PBR이 비현실적으로 낮아지는 문제 해결.

    KR 종목: IMF/금융위기 극단값 제거를 위해 2010-01-01 이후 데이터만 사용.
    US 종목: STATS_YEARS 기준 전체 역사 데이터 사용.
    """
    try:
        end = date.today()
        if ticker.endswith(".KS") or ticker.endswith(".KQ"):
            start = date(2010, 1, 1)
        else:
            start = end - timedelta(days=365 * STATS_YEARS)
        tk = yf.Ticker(ticker)

        hist = tk.history(start=start.isoformat(), end=end.isoformat(), auto_adjust=True)
        if hist.empty:
            return None

        pbr_series = _calc_historical_pbr(tk, hist)
        if pbr_series is None or pbr_series.empty:
            _log("warning", "pbr_series_empty", ticker=ticker)
            return None

        return StockStatsRecord(
            ticker=ticker,
            stat_type="PBR_STATS",
            pbr_min_value=round(float(pbr_series.min()), 4),
            pbr_max_value=round(float(pbr_series.max()), 4),
            pbr_median_value=round(float(pbr_series.median()), 4),
            years_of_data=STATS_YEARS,
            updated_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        _log("warning", "pbr_stats_failed", ticker=ticker, error=str(e))
        return None


def _calc_historical_pbr(tk, hist) -> Optional[object]:
    """
    연간+분기 balance sheet BPS를 일별 forward-fill하여 시계열 PBR 계산.
    - 연간(4년) + 분기(4~5분기) 합산으로 커버리지 확대
    - timezone-aware hist index를 tz-naive로 정규화하여 KR 종목 호환
    - fallback: tk.info.bookValue (단일값)
    """
    import pandas as pd

    def _bps_from_bs(bs) -> Optional[pd.Series]:
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
            # KR 종목은 hist가 최대 16년(2010~)이지만 balance_sheet는 4년만 제공.
            # 유효 커버리지 10% 이상이면 충분히 신뢰 가능한 PBR 계산 가능.
            coverage_threshold = 0.1 if (tk.ticker.endswith(".KS") or tk.ticker.endswith(".KQ")) else 0.3
            if len(valid) >= len(hist_norm) * coverage_threshold:
                pbr = (hist_norm["Close"] / bps_daily).dropna().round(4)
                result = pbr[pbr > 0]
                if not result.empty:
                    return result
    except Exception:
        pass

    # fallback: tk.info.bookValue (단일값 — 정확도 낮지만 없는 것보다 나음)
    try:
        book_value = tk.info.get("bookValue")
        if book_value and float(book_value) > 0:
            pbr = (hist_norm["Close"] / float(book_value)).dropna().round(4)
            return pbr[pbr > 0]
    except Exception:
        pass

    return None


def handler(event: dict, context) -> dict:
    try:
        all_tickers = TICKER_LIST["KR"] + TICKER_LIST["US"]
        results = {"updated": [], "failed": []}

        for ticker in all_tickers:
            stats = recalculate_pbr_stats(ticker)
            if stats:
                db.save_stock_stats(stats, STOCK_STATS_TABLE)
                results["updated"].append(ticker)
                _log("info", "stats_updated", ticker=ticker)
            else:
                results["failed"].append(ticker)
            time.sleep(random.uniform(1, 3))

        _log("info", "stats_update_complete", **results)
        return {"statusCode": 200, "body": json.dumps(results)}
    except Exception as e:
        _log("error", "unhandled_exception", error=str(e))
        return {"statusCode": 500, "body": "Internal error"}
