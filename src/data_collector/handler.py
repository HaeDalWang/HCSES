"""
DataCollector Lambda 핸들러
Bulkhead 패턴, 전역 예외 처리 (SECURITY-15), 구조화 로깅 (SECURITY-03)
"""
import json
import logging
import os
import random
import time
from datetime import date, datetime

from src.data_collector.ingestion_service import (
    collect_stock_data,
    collect_kr_supply_demand,
    collect_market_indicators,
)
from src.shared import dynamodb_client as db
from src.shared.market_calendar import is_market_holiday

# 구조화 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STOCK_DAILY_TABLE = os.environ.get("STOCK_DAILY_TABLE", "hcses-stock-daily")
MARKET_INDICATOR_TABLE = os.environ.get("MARKET_INDICATOR_TABLE", "hcses-market-indicator")

# 종목 목록 (실운영 시 DynamoDB 설정 테이블 또는 환경변수로 관리)
TICKER_LIST: dict[str, list[str]] = {
    "KR": ["005930.KS", "000660.KS", "035420.KS", "051910.KS", "006400.KS"],
    "US": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
}


def _log(level: str, message: str, **kwargs) -> None:
    """SECURITY-03: 구조화 로그. 민감 데이터 절대 포함 금지."""
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
    market = event.get("market", os.environ.get("MARKET", "KR"))
    today = date.today()
    correlation_id = getattr(context, "aws_request_id", "local")

    _log("info", "collection_start", market=market, date=today.isoformat(),
         correlation_id=correlation_id)

    # BR-05: 휴장일 체크
    if is_market_holiday(market, today):
        _log("info", "market_holiday_skip", market=market, date=today.isoformat())
        return {"statusCode": 200, "body": "holiday_skip"}

    tickers = TICKER_LIST.get(market, [])
    results = {"success": [], "failed": [], "skipped": []}

    for ticker in tickers:
        try:
            # 수집
            record = collect_stock_data(ticker, market, today)
            if record is None:
                results["skipped"].append(ticker)
                continue

            # KR 수급 데이터 병합
            if market == "KR":
                f_val, i_val = collect_kr_supply_demand(ticker, today)
                record.foreign_net_buy_value = f_val
                record.institution_net_buy_value = i_val

            # DynamoDB 저장 (TC-01 멱등성)
            record.data_status = "COMPLETE"
            saved = db.save_stock_daily(record, STOCK_DAILY_TABLE)
            if saved:
                results["success"].append(ticker)
                _log("info", "ticker_saved", ticker=ticker, market=market)
            else:
                results["failed"].append(ticker)

        except Exception as e:
            # Bulkhead: 단일 종목 실패 격리
            _log("warning", "ticker_collection_failed", ticker=ticker, error=str(e))
            try:
                db.update_data_status(ticker, today.isoformat(), "FAILED", STOCK_DAILY_TABLE)
            except Exception:
                pass
            results["failed"].append(ticker)

        # BR-04: Rate Limiting
        time.sleep(random.uniform(1, 3))

    # 시장 지표 수집
    try:
        indicators = collect_market_indicators(today)
        for ind in indicators:
            db.save_market_indicator(ind, MARKET_INDICATOR_TABLE)
        _log("info", "indicators_saved", count=len(indicators))
    except Exception as e:
        _log("error", "indicators_collection_failed", error=str(e))

    _log("info", "collection_complete", market=market, **results)
    return {"statusCode": 200, "body": json.dumps(results)}
