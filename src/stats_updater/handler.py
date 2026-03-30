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

logging.basicConfig(level=logging.INFO)
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
    KR 종목: quarterly_balance_sheet에서 BPS 직접 계산 (bookValue가 None이므로)
    US 종목: tk.info.bookValue 기반 근사
    StockStatsTable에는 순수 원본 값만 저장 (팩터 미적용).
    """
    try:
        end = date.today()
        start = end - timedelta(days=365 * STATS_YEARS)
        tk = yf.Ticker(ticker)

        hist = tk.history(start=start.isoformat(), end=end.isoformat(), auto_adjust=True)
        if hist.empty:
            return None

        bps = None

        # 1차: balance sheet에서 BPS 직접 계산 (KR/US 공통 시도)
        bs = tk.quarterly_balance_sheet
        if bs is not None and not bs.empty:
            if "Stockholders Equity" in bs.index and "Ordinary Shares Number" in bs.index:
                equity = bs.loc["Stockholders Equity"].iloc[0]
                shares = bs.loc["Ordinary Shares Number"].iloc[0]
                if equity and shares and float(shares) > 0:
                    bps = float(equity) / float(shares)

        # 2차: tk.info.bookValue fallback (US 종목)
        if not bps or bps <= 0:
            book_value = tk.info.get("bookValue")
            if book_value and float(book_value) > 0:
                bps = float(book_value)

        if not bps or bps <= 0:
            _log("warning", "bps_unavailable", ticker=ticker)
            return None

        pbr_series = (hist["Close"] / bps).dropna()
        if pbr_series.empty:
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
