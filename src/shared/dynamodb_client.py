"""
DynamoDB 공통 클라이언트
TC-01: 멱등성 쓰기 헬퍼 포함
"""
import os
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from src.shared.models import StockDailyRecord, MarketIndicatorRecord, StockStatsRecord

logger = logging.getLogger(__name__)


def _to_dynamodb_item(d: dict) -> dict:
    """float → Decimal 변환. DynamoDB는 Python float을 거부함."""
    converted = {}
    for k, v in d.items():
        if isinstance(v, float):
            converted[k] = Decimal(str(v))
        elif v is not None:
            converted[k] = v
    return converted

_dynamodb = None


def get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    return _dynamodb


def calc_ttl(days: int = 180) -> int:
    return int((datetime.utcnow() + timedelta(days=days)).timestamp())


def save_stock_daily(record: StockDailyRecord, table_name: str) -> bool:
    """
    TC-01 멱등성: COMPLETE 레코드는 덮어쓰기 금지.
    FAILED 레코드는 재시도 허용 (UpdateItem).
    """
    table = get_dynamodb().Table(table_name)
    item = _to_dynamodb_item({k: v for k, v in record.__dict__.items() if v is not None})
    item["ttl"] = calc_ttl(180)

    try:
        # COMPLETE 레코드 존재 시 skip
        table.put_item(
            Item=item,
            ConditionExpression=(
                Attr("ticker").not_exists() |
                Attr("data_status").eq("FAILED")
            )
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info(f"idempotent_skip ticker={record.ticker} date={record.date}")
            return True
        logger.error(f"dynamodb_put_failed ticker={record.ticker} error={str(e)}")
        return False


def update_data_status(ticker: str, date: str, status: str, table_name: str) -> None:
    table = get_dynamodb().Table(table_name)
    table.update_item(
        Key={"ticker": ticker, "date": date},
        UpdateExpression="SET data_status = :s",
        ExpressionAttributeValues={":s": status}
    )


def update_analysis_status(ticker: str, date: str, table_name: str) -> None:
    table = get_dynamodb().Table(table_name)
    table.update_item(
        Key={"ticker": ticker, "date": date},
        UpdateExpression="SET analysis_status = :s",
        ExpressionAttributeValues={":s": "DONE"}
    )


def save_market_indicator(record: MarketIndicatorRecord, table_name: str) -> bool:
    table = get_dynamodb().Table(table_name)
    item = _to_dynamodb_item({k: v for k, v in record.__dict__.items() if v is not None})
    item["ttl"] = calc_ttl(180)
    try:
        table.put_item(Item=item)
        return True
    except ClientError as e:
        logger.error(f"dynamodb_indicator_failed indicator={record.indicator} error={str(e)}")
        return False


def get_latest_complete_record(ticker: str, date: str, table_name: str) -> Optional[dict]:
    """data_status=COMPLETE AND analysis_status=PENDING 레코드 조회"""
    table = get_dynamodb().Table(table_name)
    try:
        resp = table.get_item(Key={"ticker": ticker, "date": date})
        item = resp.get("Item")
        if item and item.get("data_status") == "COMPLETE" and item.get("analysis_status") != "DONE":
            return item
        return None
    except ClientError as e:
        logger.error(f"dynamodb_get_failed ticker={ticker} error={str(e)}")
        return None


def save_stock_stats(record: StockStatsRecord, table_name: str) -> bool:
    table = get_dynamodb().Table(table_name)
    item = _to_dynamodb_item({k: v for k, v in record.__dict__.items() if v is not None})
    try:
        table.put_item(Item=item)
        return True
    except ClientError as e:
        logger.error(f"dynamodb_stats_failed ticker={record.ticker} error={str(e)}")
        return False
