"""AlertingEngine handler.py 단위 테스트"""
import pytest
from unittest.mock import patch, MagicMock

from src.alerting_engine import handler as h


class FakeContext:
    aws_request_id = "test-id"


def _event():
    return {
        "ticker": "005930.KS", "market": "KR", "date": "2026-03-29",
        "current_price_value": 75000.0,
        "pbr_median_value": 1.2, "pbr_min_value": 0.4,
        "breakdown": {
            "total_score": 100.0, "valuation_score": 40.0,
            "momentum_score": 30.0, "supply_demand_score": 30.0,
            "signals": ["ValuationFloor", "MomentumPivot"],
            "pbr_value": 0.55,
        },
    }


@patch("src.alerting_engine.handler.get_secret", return_value={"webhook_url": "https://discord.com/test"})
@patch("src.alerting_engine.handler.send_discord_alert", return_value=True)
def test_handler_success(mock_send, mock_secret):
    result = h.handler(_event(), FakeContext())
    assert result["statusCode"] == 200
    assert "alert_sent" in result["body"]


@patch("src.alerting_engine.handler.get_secret", return_value={"webhook_url": "https://discord.com/test"})
@patch("src.alerting_engine.handler.send_discord_alert", return_value=False)
def test_handler_send_failure(mock_send, mock_secret):
    result = h.handler(_event(), FakeContext())
    assert result["statusCode"] == 500


@patch("src.alerting_engine.handler.get_secret", return_value={})
def test_handler_missing_webhook_url(mock_secret):
    result = h.handler(_event(), FakeContext())
    assert result["statusCode"] == 500
    assert "webhook_url_missing" in result["body"]


@patch("src.alerting_engine.handler._run", side_effect=Exception("fatal"))
def test_global_exception_returns_500(mock_run):
    result = h.handler({}, FakeContext())
    assert result["statusCode"] == 500
