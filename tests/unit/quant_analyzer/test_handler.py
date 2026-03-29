"""QuantAnalyzer handler.py 단위 테스트"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.quant_analyzer import handler as h


class FakeContext:
    aws_request_id = "test-id"


@patch("src.quant_analyzer.handler.is_within_market_hours", return_value=False)
def test_outside_market_hours_returns_early(mock_hours):
    result = h.handler({"market": "KR"}, FakeContext())
    assert result["statusCode"] == 200
    assert "outside_market_hours" in result["body"]


@patch("src.quant_analyzer.handler.is_within_market_hours", return_value=True)
@patch("src.quant_analyzer.handler.is_market_holiday", return_value=True)
def test_holiday_skip(mock_holiday, mock_hours):
    result = h.handler({"market": "KR"}, FakeContext())
    assert "holiday_skip" in result["body"]


@patch("src.quant_analyzer.handler.is_within_market_hours", return_value=True)
@patch("src.quant_analyzer.handler.is_market_holiday", return_value=False)
@patch("src.quant_analyzer.handler.load_market_indicators", return_value={})
@patch("src.quant_analyzer.handler.evaluate_kill_switch")
def test_kill_switch_active_returns_early(mock_ks, mock_ind, mock_holiday, mock_hours):
    from src.shared.scoring import KillSwitchResult
    mock_ks.return_value = KillSwitchResult(active=True, reason="VIX=35>30")
    result = h.handler({"market": "KR"}, FakeContext())
    assert "kill_switch" in result["body"]


@patch("src.quant_analyzer.handler.is_within_market_hours", return_value=True)
@patch("src.quant_analyzer.handler.is_market_holiday", return_value=False)
@patch("src.quant_analyzer.handler.load_market_indicators", return_value={})
@patch("src.quant_analyzer.handler.evaluate_kill_switch")
@patch("src.quant_analyzer.handler.db.get_latest_complete_record", return_value=None)
def test_no_complete_records_all_skipped(mock_rec, mock_ks, mock_ind, mock_holiday, mock_hours):
    from src.shared.scoring import KillSwitchResult
    mock_ks.return_value = KillSwitchResult(active=False)
    result = h.handler({"market": "US"}, FakeContext())
    import json
    body = json.loads(result["body"])
    assert len(body["skipped"]) > 0


@patch("src.quant_analyzer.handler._run", side_effect=Exception("fatal"))
def test_global_exception_returns_500(mock_run):
    result = h.handler({}, FakeContext())
    assert result["statusCode"] == 500


@patch("src.quant_analyzer.handler.is_within_market_hours", return_value=True)
@patch("src.quant_analyzer.handler.is_market_holiday", return_value=False)
@patch("src.quant_analyzer.handler.load_market_indicators", return_value={})
@patch("src.quant_analyzer.handler.evaluate_kill_switch")
@patch("src.quant_analyzer.handler.db.get_latest_complete_record")
@patch("src.quant_analyzer.handler.get_stock_stats", return_value=None)
@patch("src.quant_analyzer.handler.build_scoring_context")
@patch("src.quant_analyzer.handler.calculate_total_score")
@patch("src.quant_analyzer.handler._invoke_alerting_engine", return_value=False)
@patch("src.quant_analyzer.handler.db.update_analysis_status")
def test_alert_fail_keeps_analysis_status_pending(
    mock_update, mock_invoke, mock_score, mock_ctx,
    mock_stats, mock_rec, mock_ks, mock_ind, mock_holiday, mock_hours
):
    """알람 발송 실패 시 analysis_status=DONE 업데이트 금지 → 다음 실행에서 재시도"""
    from src.shared.scoring import KillSwitchResult, ScoreBreakdown, ScoringContext
    mock_ks.return_value = KillSwitchResult(active=False)
    mock_rec.return_value = {"ticker": "AAPL", "data_status": "COMPLETE"}
    mock_ctx.return_value = ScoringContext(ticker="AAPL", market="US", date="2026-03-29")
    bd = ScoreBreakdown(ticker="AAPL", market="US", date="2026-03-29", total_score=95.0)
    mock_score.return_value = bd

    h.handler({"market": "US"}, FakeContext())

    # 알람 실패 → update_analysis_status 호출 안 됨
    mock_update.assert_not_called()
