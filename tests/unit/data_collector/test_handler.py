"""DataCollector handler.py 단위 테스트"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from src.data_collector import handler as h


class FakeContext:
    aws_request_id = "test-correlation-id"


@patch("src.data_collector.handler.is_market_holiday", return_value=True)
def test_holiday_returns_skip(mock_holiday):
    result = h.handler({"market": "KR"}, FakeContext())
    assert result["statusCode"] == 200
    assert "holiday_skip" in result["body"]


@patch("src.data_collector.handler.is_market_holiday", return_value=False)
@patch("src.data_collector.handler.collect_stock_data", return_value=None)
@patch("src.data_collector.handler.collect_market_indicators", return_value=[])
@patch("src.data_collector.handler.db.save_market_indicator")
def test_none_record_goes_to_skipped(mock_save_ind, mock_ind, mock_collect, mock_holiday):
    result = h.handler({"market": "US"}, FakeContext())
    assert result["statusCode"] == 200
    import json
    body = json.loads(result["body"])
    assert len(body["skipped"]) > 0


@patch("src.data_collector.handler.is_market_holiday", return_value=False)
@patch("src.data_collector.handler.collect_stock_data", side_effect=Exception("API error"))
@patch("src.data_collector.handler.collect_market_indicators", return_value=[])
@patch("src.data_collector.handler.db.save_market_indicator")
@patch("src.data_collector.handler.db.update_data_status")
def test_bulkhead_single_ticker_failure_continues(
    mock_status, mock_save_ind, mock_ind, mock_collect, mock_holiday
):
    """Bulkhead: 단일 종목 예외가 전체 실행을 중단하지 않음"""
    result = h.handler({"market": "US"}, FakeContext())
    assert result["statusCode"] == 200
    import json
    body = json.loads(result["body"])
    # 모든 종목이 failed로 기록되지만 handler는 200 반환
    assert isinstance(body["failed"], list)


@patch("src.data_collector.handler._run", side_effect=Exception("fatal"))
def test_global_exception_handler_returns_500(mock_run):
    result = h.handler({}, FakeContext())
    assert result["statusCode"] == 500
