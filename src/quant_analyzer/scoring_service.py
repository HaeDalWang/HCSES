"""
QuantAnalyzer 스코어링 서비스
DynamoDB 조회 + ScoringContext 빌드 + 20거래일 누적합 계산 + ATR(14)
"""
import json
import logging
import os
from datetime import date, timedelta
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from src.shared.scoring import ScoringContext
from src.shared import dynamodb_client as db

logger = logging.getLogger(__name__)

STOCK_DAILY_TABLE = os.environ.get("STOCK_DAILY_TABLE", "hcses-stock-daily")
STOCK_STATS_TABLE = os.environ.get("STOCK_STATS_TABLE", "hcses-stock-stats")
MARKET_INDICATOR_TABLE = os.environ.get("MARKET_INDICATOR_TABLE", "hcses-market-indicator")


def load_market_indicators(target_date: date) -> dict:
    """
    VIX, US10Y, KRWUSD 당일 지표 로드.
    당일 데이터 없으면 전일 데이터 fallback — stale=True 플래그 포함.
    """
    table = db.get_dynamodb().Table(MARKET_INDICATOR_TABLE)
    result = {}
    prev_date = (target_date - timedelta(days=1)).isoformat()

    for indicator in ["VIX", "US10Y", "KRWUSD"]:
        try:
            resp = table.get_item(Key={"indicator": indicator, "date": target_date.isoformat()})
            item = resp.get("Item")
            if item:
                item["stale"] = False
                result[indicator] = item
            else:
                resp2 = table.get_item(Key={"indicator": indicator, "date": prev_date})
                item2 = resp2.get("Item")
                if item2:
                    item2["stale"] = True
                    result[indicator] = item2
                    logger.warning(json.dumps({
                        "level": "WARNING", "message": "stale_indicator_used",
                        "indicator": indicator,
                        "expected_date": target_date.isoformat(), "actual_date": prev_date,
                    }))
                else:
                    logger.warning(json.dumps({
                        "level": "WARNING", "message": "indicator_unavailable",
                        "indicator": indicator, "date": target_date.isoformat(),
                    }))
        except ClientError as e:
            logger.warning(f"indicator_load_failed indicator={indicator} error={str(e)}")
    return result


def get_stock_stats(ticker: str) -> Optional[dict]:
    """StockStatsTable에서 PBR 통계 조회"""
    table = db.get_dynamodb().Table(STOCK_STATS_TABLE)
    try:
        resp = table.get_item(Key={"ticker": ticker, "stat_type": "PBR_STATS"})
        return resp.get("Item")
    except ClientError as e:
        logger.warning(f"stats_load_failed ticker={ticker} error={str(e)}")
        return None


def _get_prev_rsi(ticker: str, target_date: date) -> Optional[float]:
    """전일 RSI 조회. 주말+공휴일 건너뛰기 (최대 7일 탐색)."""
    prev_date = target_date - timedelta(days=1)
    for _ in range(7):
        if prev_date.weekday() < 5:
            record = db.get_latest_complete_record(ticker, prev_date.isoformat(), STOCK_DAILY_TABLE)
            if record:
                return record.get("rsi_level")
        prev_date -= timedelta(days=1)
    return None


def _calc_cumulative_net_buy(ticker: str, target_date: date) -> tuple[Optional[float], Optional[float]]:
    """최근 20거래일 외국인+기관 누적 순매수합. 반환: (today, prev)"""
    table = db.get_dynamodb().Table(STOCK_DAILY_TABLE)
    try:
        start = (target_date - timedelta(days=30)).isoformat()
        end = target_date.isoformat()
        resp = table.query(
            KeyConditionExpression=Key("ticker").eq(ticker) & Key("date").between(start, end),
            FilterExpression=Attr("data_status").eq("COMPLETE"),
        )
        items = sorted(resp.get("Items", []), key=lambda x: x["date"])
        recent = items[-20:] if len(items) >= 20 else items
        prev_20 = items[-21:-1] if len(items) >= 21 else items[:-1]

        def _sum(rows):
            total = 0.0
            for r in rows:
                f = r.get("foreign_net_buy_value") or 0.0
                i = r.get("institution_net_buy_value") or 0.0
                total += float(f) + float(i)
            return round(total, 4)

        return (_sum(recent) if recent else None, _sum(prev_20) if prev_20 else None)
    except ClientError as e:
        logger.warning(f"cumulative_net_buy_failed ticker={ticker} error={str(e)}")
        return None, None


def _calc_atr(ticker: str, target_date: date, period: int = 14) -> Optional[float]:
    """
    ATR(14) — DynamoDB StockDailyTable의 최근 15거래일 OHLC 사용.
    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    Wilder's Smoothing 적용.
    """
    table = db.get_dynamodb().Table(STOCK_DAILY_TABLE)
    try:
        start = (target_date - timedelta(days=30)).isoformat()
        end = target_date.isoformat()
        resp = table.query(
            KeyConditionExpression=Key("ticker").eq(ticker) & Key("date").between(start, end),
            FilterExpression=Attr("data_status").eq("COMPLETE"),
        )
        items = sorted(resp.get("Items", []), key=lambda x: x["date"])
        recent = items[-(period + 1):]

        if len(recent) < period + 1:
            return None

        true_ranges = []
        for i in range(1, len(recent)):
            high = float(recent[i].get("high_value") or 0)
            low = float(recent[i].get("low_value") or 0)
            prev_close = float(recent[i - 1].get("close_value") or 0)
            if not high or not low or not prev_close:
                return None
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return None

        atr = sum(true_ranges[:period]) / period
        for tr in true_ranges[period:]:
            atr = (atr * (period - 1) + tr) / period

        return round(atr, 4)
    except ClientError as e:
        logger.warning(f"atr_calc_failed ticker={ticker} error={str(e)}")
        return None


def build_scoring_context(
    record: dict, stats: Optional[dict], ticker: str, market: str, target_date: date
) -> tuple[ScoringContext, Optional[float]]:
    """DynamoDB 레코드 + 통계 → ScoringContext 빌드. ATR(14)도 함께 반환."""
    pbr_min_value = None
    if stats:
        pbr_min_value = stats.get("pbr_min_value")
        if pbr_min_value is not None:
            pbr_min_value = float(pbr_min_value)

    rsi_prev_level = _get_prev_rsi(ticker, target_date)

    cum_today, cum_prev = None, None
    if market == "KR":
        cum_today, cum_prev = _calc_cumulative_net_buy(ticker, target_date)

    atr_value = _calc_atr(ticker, target_date)

    ctx = ScoringContext(
        ticker=ticker,
        market=market,
        date=target_date.isoformat(),
        pbr_value=float(record["pbr_value"]) if record.get("pbr_value") is not None else None,
        pbr_min_value=pbr_min_value,
        close_value=float(record["close_value"]) if record.get("close_value") is not None else None,
        ma20_value=float(record["ma20_value"]) if record.get("ma20_value") is not None else None,
        rsi_prev_level=float(rsi_prev_level) if rsi_prev_level is not None else None,
        rsi_curr_level=float(record["rsi_level"]) if record.get("rsi_level") is not None else None,
        cumulative_net_buy_value=cum_today,
        prev_cumulative_net_buy_value=cum_prev,
    )
    return ctx, atr_value
