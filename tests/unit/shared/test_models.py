"""shared/models.py 단위 테스트"""
import pytest
from src.shared.models import StockDailyRecord, MarketIndicatorRecord, AnalysisResult


def test_stock_daily_record_defaults():
    r = StockDailyRecord(ticker="005930.KS", market="KR", date="2026-03-29")
    assert r.data_status == "COLLECTING"
    assert r.analysis_status == "PENDING"
    assert r.pbr_value is None


def test_market_indicator_record():
    r = MarketIndicatorRecord(indicator="VIX", date="2026-03-29", value_value=18.5)
    assert r.indicator == "VIX"
    assert r.change_pct is None


def test_analysis_result_defaults():
    r = AnalysisResult(ticker="AAPL", market="US", date="2026-03-29")
    assert r.total_score == 0.0
    assert r.kill_switch_active is False
    assert r.signals == []
