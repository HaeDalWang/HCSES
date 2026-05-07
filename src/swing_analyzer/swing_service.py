"""
SwingAnalyzer 서비스 — DynamoDB 조회 + 파생 지표 계산 + SwingContext 빌드
기존 DataCollector가 수집한 데이터를 Read-Only로 사용.
"""
import logging
import os
from datetime import date, timedelta
from typing import Optional

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from src.shared import dynamodb_client as db
from src.swing_analyzer.swing_scoring import SwingContext, COOLDOWN_DAYS

logger = logging.getLogger(__name__)

STOCK_DAILY_TABLE = os.environ.get("STOCK_DAILY_TABLE", "hcses-stock-daily")
MARKET_INDICATOR_TABLE = os.environ.get("MARKET_INDICATOR_TABLE", "hcses-market-indicator")
SWING_COOLDOWN_TABLE = os.environ.get("SWING_COOLDOWN_TABLE", "hcses-swing-cooldown")


def _query_recent_records(ticker: str, target_date: date, days: int = 30) -> list[dict]:
    """최근 N일 COMPLETE 레코드를 날짜순 정렬 반환. 페이지네이션 처리."""
    table = db.get_dynamodb().Table(STOCK_DAILY_TABLE)
    start = (target_date - timedelta(days=days)).isoformat()
    end = target_date.isoformat()
    try:
        items = []
        query_params = {
            "KeyConditionExpression": Key("ticker").eq(ticker) & Key("date").between(start, end),
            "FilterExpression": Attr("data_status").eq("COMPLETE"),
        }
        resp = table.query(**query_params)
        items.extend(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            query_params["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
            resp = table.query(**query_params)
            items.extend(resp.get("Items", []))
        return sorted(items, key=lambda x: x["date"])
    except ClientError as e:
        logger.warning(f"query_recent_failed ticker={ticker} error={str(e)}")
        return []


def _calc_ma(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return round(sum(values[-period:]) / period, 4)


def _calc_bollinger_lower(closes: list[float], period: int = 20, num_std: float = 2.0) -> Optional[float]:
    if len(closes) < period:
        return None
    window = closes[-period:]
    ma = sum(window) / period
    variance = sum((x - ma) ** 2 for x in window) / period
    std = variance ** 0.5
    return round(ma - num_std * std, 4)


def _calc_atr(records: list[dict], period: int = 14) -> Optional[float]:
    """ATR(14) — Wilder's Smoothing."""
    if len(records) < period + 1:
        return None
    recent = records[-(period + 1):]
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
    if atr == 0:
        return None
    for tr in true_ranges[period:]:
        atr = (atr * (period - 1) + tr) / period
    return round(atr, 4)


def build_swing_context(ticker: str, market: str, target_date: date) -> Optional[SwingContext]:
    """DynamoDB 레코드에서 SwingContext를 빌드. 데이터 부족 시 None."""
    records = _query_recent_records(ticker, target_date, days=35)
    if len(records) < 20:
        return None

    today_rec = records[-1]
    if today_rec["date"] != target_date.isoformat():
        return None

    prev_rec = records[-2] if len(records) >= 2 else None
    prev_prev_rec = records[-3] if len(records) >= 3 else None

    closes = [float(r["close_value"]) for r in records if r.get("close_value")]
    volumes = [int(r["volume_value"]) for r in records if r.get("volume_value")]

    ma5_value = _calc_ma(closes, 5)
    ma5_prev_value = _calc_ma(closes[:-1], 5) if len(closes) > 5 else None
    ma20_value = _calc_ma(closes, 20)
    bb_lower_value = _calc_bollinger_lower(closes, 20, 2.0)
    volume_ma20 = _calc_ma([float(v) for v in volumes], 20)
    atr_value = _calc_atr(records, 14)

    rsi_curr = _safe_float(today_rec.get("rsi_level"))
    rsi_prev = _safe_float(prev_rec.get("rsi_level")) if prev_rec else None
    rsi_prev_prev = _safe_float(prev_prev_rec.get("rsi_level")) if prev_prev_rec else None

    return SwingContext(
        ticker=ticker,
        market=market,
        date=target_date.isoformat(),
        close_value=_safe_float(today_rec.get("close_value")),
        close_prev_value=_safe_float(prev_rec.get("close_value")) if prev_rec else None,
        low_prev_value=_safe_float(prev_rec.get("low_value")) if prev_rec else None,
        ma5_value=ma5_value,
        ma5_prev_value=ma5_prev_value,
        ma20_value=ma20_value,
        rsi_curr_level=rsi_curr,
        rsi_prev_level=rsi_prev,
        rsi_prev_prev_level=rsi_prev_prev,
        bb_lower_value=bb_lower_value,
        volume_value=int(today_rec.get("volume_value") or 0) or None,
        volume_ma20_value=volume_ma20,
        foreign_net_buy_value=_safe_float(today_rec.get("foreign_net_buy_value")),
        institution_net_buy_value=_safe_float(today_rec.get("institution_net_buy_value")),
        atr_value=atr_value,
    )


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def load_vix_value(target_date: date) -> Optional[float]:
    """당일 VIX 조회. 없으면 전일 fallback."""
    table = db.get_dynamodb().Table(MARKET_INDICATOR_TABLE)
    for offset in range(2):
        d = (target_date - timedelta(days=offset)).isoformat()
        try:
            resp = table.get_item(Key={"indicator": "VIX", "date": d})
            item = resp.get("Item")
            if item and item.get("value_value") is not None:
                return float(item["value_value"])
        except ClientError:
            pass
    return None


def is_in_cooldown(ticker: str, target_date: date) -> bool:
    """동일 종목 최근 10거래일 내 Tier 2 알림 발송 여부 확인."""
    table = db.get_dynamodb().Table(SWING_COOLDOWN_TABLE)
    try:
        resp = table.get_item(Key={"ticker": ticker})
        item = resp.get("Item")
        if not item:
            return False
        last_alert_date = item.get("last_alert_date", "")
        if not last_alert_date:
            return False
        cooldown_end = date.fromisoformat(last_alert_date) + timedelta(days=COOLDOWN_DAYS)
        return target_date <= cooldown_end
    except ClientError:
        return False


def record_cooldown(ticker: str, alert_date: date) -> None:
    """알림 발송 후 쿨다운 기록."""
    table = db.get_dynamodb().Table(SWING_COOLDOWN_TABLE)
    try:
        table.put_item(Item={
            "ticker": ticker,
            "last_alert_date": alert_date.isoformat(),
            "ttl": db.calc_ttl(30),
        })
    except ClientError as e:
        logger.warning(f"cooldown_record_failed ticker={ticker} error={str(e)}")


def calc_exit_strategy(
    close_value: float, ma20_value: Optional[float], atr_value: Optional[float], market: str
) -> dict:
    """목표가, 손절가, 타임컷 계산."""
    # 목표가 = min(MA20, +10%)
    target_by_pct = close_value * 1.10
    if ma20_value and ma20_value > close_value:
        target_price = min(ma20_value, target_by_pct)
    else:
        target_price = target_by_pct

    # 손절가 = 진입가 - ATR × 1.5 (없으면 -5%)
    if atr_value and atr_value > 0:
        stop_loss = close_value - (atr_value * 1.5)
    else:
        stop_loss = close_value * 0.95

    if stop_loss <= 0:
        stop_loss = close_value * 0.95

    return {
        "target_price_value": round(target_price, 4),
        "stop_loss_value": round(stop_loss, 4),
        "timecut_days": 15,
    }
