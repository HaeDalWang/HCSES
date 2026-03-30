"""
AlertingEngine Lambda 핸들러
TC-02 (Secret 캐싱), TC-03 (2000자 제한), SECURITY-03, 15
"""
import json
import logging
import os
from datetime import datetime

from src.alerting_engine.alert_service import (
    calc_target_price,
    calc_stop_loss_atr,
    format_alert_message,
    truncate_if_needed,
    send_discord_alert,
)
from src.shared.secrets_cache import get_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_NAME = os.environ.get("DISCORD_SECRET_NAME", "hcses/discord-webhook-url")


def _log(level: str, message: str, **kwargs) -> None:
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        json.dumps({"timestamp": datetime.utcnow().isoformat(), "level": level,
                    "message": message, **kwargs})
    )


def handler(event: dict, context) -> dict:
    """Lambda 진입점. SECURITY-15: 전역 예외 처리."""
    try:
        return _run(event, context)
    except Exception as e:
        _log("error", "unhandled_exception", error=str(e))
        return {"statusCode": 500, "body": "Internal error"}


def _run(event: dict, context) -> dict:
    # TC-02: Secrets Manager 전역 캐싱
    secret = get_secret(SECRET_NAME)
    webhook_url = secret.get("webhook_url") or secret.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        _log("error", "webhook_url_missing")
        return {"statusCode": 500, "body": "webhook_url_missing"}

    ticker = event.get("ticker", "UNKNOWN")
    ticker_name = event.get("ticker_name", ticker)
    market = event.get("market", "KR")
    date = event.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
    breakdown = event.get("breakdown", {})
    current_price_value = float(event.get("current_price_value") or 0)
    pbr_value = breakdown.get("pbr_value") or event.get("pbr_value")
    pbr_median_value = event.get("pbr_median_value")
    atr_value = event.get("atr_value")

    # 목표가: PBR Median 기반 (유지)
    target_price_str = calc_target_price(current_price_value, pbr_median_value, pbr_value, market)

    # 손절가: ATR(14) 기반 — 현재가 - 1.5 × ATR
    # ATR 없으면 N/A (보수적 원칙)
    stop_loss_price_str = calc_stop_loss_atr(current_price_value, atr_value, market)

    # BR-01: 메시지 포맷
    message = format_alert_message(
        ticker=ticker,
        ticker_name=ticker_name,
        market=market,
        date=date,
        current_price_value=current_price_value,
        target_price_str=target_price_str,
        stop_loss_price_str=stop_loss_price_str,
        breakdown=breakdown,
    )

    # BR-03: 2,000자 제한
    message = truncate_if_needed(message)

    # BR-05: 발송 (최대 3회 재시도)
    success = send_discord_alert(webhook_url, message)

    if success:
        _log("info", "alert_sent", ticker=ticker, market=market, score=breakdown.get("total_score"))
        return {"statusCode": 200, "body": "alert_sent"}
    else:
        _log("error", "alert_failed", ticker=ticker)
        return {"statusCode": 500, "body": "alert_failed"}
