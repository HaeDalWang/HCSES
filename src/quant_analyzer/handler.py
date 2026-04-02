"""
QuantAnalyzer Lambda 핸들러
DST 검증, Kill-Switch, Bulkhead, AlertingEngine 호출
"""
import json
import logging
import os
from datetime import date, datetime

import boto3

from src.quant_analyzer.scoring_service import (
    load_market_indicators,
    get_stock_stats,
    build_scoring_context,
)
from src.shared import dynamodb_client as db
from src.shared.market_calendar import is_within_market_hours, is_market_holiday
from src.shared.scoring import evaluate_kill_switch, calculate_total_score, ALERT_THRESHOLD
from src.data_collector.handler import TICKER_LIST, TICKER_NAMES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STOCK_DAILY_TABLE = os.environ.get("STOCK_DAILY_TABLE", "hcses-stock-daily")
ALERTING_ENGINE_ARN = os.environ.get("ALERTING_ENGINE_ARN", "")

_lambda_client = None


def _get_lambda_client():
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    return _lambda_client


def _log(level: str, message: str, **kwargs) -> None:
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        json.dumps({"timestamp": datetime.utcnow().isoformat(), "level": level,
                    "message": message, **kwargs})
    )


def _invoke_alerting_engine(payload: dict) -> bool:
    """AlertingEngine Lambda 동기 호출. 성공 시 True, 실패 시 False 반환."""
    try:
        _get_lambda_client().invoke(
            FunctionName=ALERTING_ENGINE_ARN,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode(),
        )
        _log("info", "alerting_engine_invoked", ticker=payload.get("ticker"))
        return True
    except Exception as e:
        _log("error", "alerting_engine_invoke_failed", ticker=payload.get("ticker"), error=str(e))
        return False


def handler(event: dict, context) -> dict:
    """Lambda 진입점. SECURITY-15: 전역 예외 처리."""
    try:
        return _run(event, context)
    except Exception as e:
        _log("error", "unhandled_exception", error=str(e))
        return {"statusCode": 500, "body": "Internal error"}


def _run(event: dict, context) -> dict:
    market = event.get("market", os.environ.get("MARKET", "KR"))
    today = date.today()
    now = datetime.utcnow()
    correlation_id = getattr(context, "aws_request_id", "local")

    # BR-08: 시장 운영 시간 검증 (TC-04 DST 반영)
    if not is_within_market_hours(market, now):
        _log("info", "outside_market_hours", market=market)
        return {"statusCode": 200, "body": "outside_market_hours"}

    # 휴장일 체크
    if is_market_holiday(market, today):
        _log("info", "market_holiday_skip", market=market)
        return {"statusCode": 200, "body": "holiday_skip"}

    # BR-02: Kill-Switch 선행 평가
    indicators = load_market_indicators(today)
    kill_switch = evaluate_kill_switch(indicators)
    if kill_switch.active:
        _log("warning", "kill_switch_active", reason=kill_switch.reason,
             correlation_id=correlation_id)
        return {"statusCode": 200, "body": f"kill_switch: {kill_switch.reason}"}

    tickers = TICKER_LIST.get(market, [])
    results = {"alerted": [], "analyzed": [], "skipped": []}

    for ticker in tickers:
        try:
            # BR-06: COMPLETE + PENDING 레코드만 처리
            record = db.get_latest_complete_record(ticker, today.isoformat(), STOCK_DAILY_TABLE)
            if record is None:
                results["skipped"].append(ticker)
                continue

            stats = get_stock_stats(ticker)
            ctx, atr_value = build_scoring_context(record, stats, ticker, market, today)
            breakdown = calculate_total_score(ctx, market, kill_switch)

            _log("info", "analysis_complete", ticker=ticker, market=market,
                 total_score=breakdown.total_score, signals=breakdown.signals,
                 correlation_id=correlation_id)

            # BR-07: 알람 임계값 — AlertingEngine 호출 먼저, 성공 후 DONE 업데이트
            # (호출 실패 시 analysis_status=PENDING 유지 → 다음 실행에서 재시도 가능)
            if breakdown.total_score >= ALERT_THRESHOLD:
                alert_ok = _invoke_alerting_engine({
                    "ticker": ticker,
                    "ticker_name": TICKER_NAMES.get(ticker, ticker),
                    "market": market,
                    "date": today.isoformat(),
                    "breakdown": breakdown.__dict__,
                    "current_price_value": ctx.close_value,
                    "pbr_min_value": ctx.pbr_min_value,
                    "pbr_median_value": stats.get("pbr_median_value") if stats else None,
                    "atr_value": atr_value,
                    "rsi_prev_level": ctx.rsi_prev_level,
                    "rsi_curr_level": ctx.rsi_curr_level,
                    "vix_value": float(indicators.get("VIX", {}).get("value_value", 0) or 0),
                    "us10y_value": float(indicators.get("US10Y", {}).get("value_value", 0) or 0),
                    "kill_switch_warning": kill_switch.reason if not kill_switch.active and kill_switch.reason else "",
                })
                if alert_ok:
                    # 알람 발송 성공 후에만 DONE 처리
                    db.update_analysis_status(ticker, today.isoformat(), STOCK_DAILY_TABLE)
                    results["alerted"].append(ticker)
                else:
                    # 알람 실패 → PENDING 유지, 다음 실행에서 재시도
                    _log("warning", "alert_failed_analysis_status_kept_pending", ticker=ticker)
            else:
                # 알람 불필요 → 바로 DONE
                db.update_analysis_status(ticker, today.isoformat(), STOCK_DAILY_TABLE)

            results["analyzed"].append(ticker)

        except Exception as e:
            # Bulkhead: 단일 종목 실패 격리
            _log("warning", "analysis_failed", ticker=ticker, error=str(e))
            continue

    _log("info", "analysis_run_complete", market=market, **results)
    return {"statusCode": 200, "body": json.dumps(results)}
