"""shared/scoring.py 단위 테스트"""
import pytest
from src.shared.scoring import (
    evaluate_kill_switch,
    calculate_valuation_floor_score,
    calculate_momentum_pivot_score,
    calculate_supply_demand_score,
    calculate_total_score,
    ScoringContext,
    KillSwitchResult,
    ALERT_THRESHOLD,
)


# ── Kill-Switch ───────────────────────────────────────────────────────────────

def test_kill_switch_vix_over_30():
    indicators = {"VIX": {"value_value": 31.5, "stale": False}, "US10Y": {}, "KRWUSD": {}}
    result = evaluate_kill_switch(indicators)
    assert result.active is True
    assert "VIX" in result.reason


def test_kill_switch_stale_vix_lower_threshold():
    """stale 지표: VIX 임계값 25로 강화"""
    indicators = {"VIX": {"value_value": 26.0, "stale": True}, "US10Y": {}, "KRWUSD": {}}
    result = evaluate_kill_switch(indicators)
    assert result.active is True
    assert "stale" in result.reason


def test_kill_switch_stale_vix_below_threshold():
    """stale 지표라도 25 미만이면 미발동"""
    indicators = {"VIX": {"value_value": 24.0, "stale": True}, "US10Y": {}, "KRWUSD": {}}
    result = evaluate_kill_switch(indicators)
    assert result.active is False


def test_kill_switch_yield_spike():
    indicators = {"VIX": {"value_value": 18.0, "stale": False},
                  "US10Y": {"change_pct": 3.5, "stale": False}, "KRWUSD": {}}
    result = evaluate_kill_switch(indicators)
    assert result.active is True
    assert "US10Y" in result.reason


def test_kill_switch_stale_yield_lower_threshold():
    """stale US10Y: 임계값 2.0%로 강화"""
    indicators = {"VIX": {"value_value": 18.0, "stale": False},
                  "US10Y": {"change_pct": 2.5, "stale": True}, "KRWUSD": {}}
    result = evaluate_kill_switch(indicators)
    assert result.active is True


def test_kill_switch_krwusd_bb_breach():
    indicators = {"VIX": {"value_value": 18.0, "stale": False},
                  "US10Y": {"change_pct": 0.5, "stale": False},
                  "KRWUSD": {"value_value": 1410.0, "bb_upper_value": 1400.0, "stale": False}}
    result = evaluate_kill_switch(indicators)
    assert result.active is True
    assert "KRWUSD" in result.reason


def test_kill_switch_inactive():
    indicators = {"VIX": {"value_value": 18.0, "stale": False},
                  "US10Y": {"change_pct": 0.5, "stale": False},
                  "KRWUSD": {"value_value": 1350.0, "bb_upper_value": 1400.0, "stale": False}}
    result = evaluate_kill_switch(indicators)
    assert result.active is False


def test_kill_switch_missing_data_no_trigger():
    """데이터 결측 시 Kill-Switch 미발동 (보수적 원칙 예외)"""
    result = evaluate_kill_switch({})
    assert result.active is False


# ── Valuation Floor ───────────────────────────────────────────────────────────

def _ctx(market="KR", **kwargs):
    return ScoringContext(ticker="TEST", market=market, date="2026-03-29", **kwargs)


def test_valuation_floor_kr_pass():
    ctx = _ctx(market="KR", pbr_value=0.55, pbr_min_value=0.5)
    score, signals = calculate_valuation_floor_score(ctx, "KR")
    assert score == 40.0
    assert len(signals) == 1


def test_valuation_floor_us_pass():
    ctx = _ctx(market="US", pbr_value=1.05, pbr_min_value=1.0)
    score, signals = calculate_valuation_floor_score(ctx, "US")
    assert score == 60.0


def test_valuation_floor_fail():
    ctx = _ctx(pbr_value=1.5, pbr_min_value=1.0)
    score, _ = calculate_valuation_floor_score(ctx, "KR")
    assert score == 0.0


def test_valuation_floor_missing_pbr():
    ctx = _ctx(pbr_value=None, pbr_min_value=0.5)
    score, _ = calculate_valuation_floor_score(ctx, "KR")
    assert score == 0.0  # BR-01 보수적 원칙


# ── Momentum Pivot ────────────────────────────────────────────────────────────

def test_momentum_pivot_kr_pass():
    ctx = _ctx(close_value=55000.0, ma20_value=50000.0,
               rsi_prev_level=28.0, rsi_curr_level=36.0)
    score, signals = calculate_momentum_pivot_score(ctx, "KR")
    assert score == 30.0
    assert len(signals) == 1


def test_momentum_pivot_rsi_not_crossed():
    ctx = _ctx(close_value=55000.0, ma20_value=50000.0,
               rsi_prev_level=32.0, rsi_curr_level=36.0)
    score, _ = calculate_momentum_pivot_score(ctx, "KR")
    assert score == 0.0  # rsi_prev > 30 → 미충족


def test_momentum_pivot_missing_data():
    ctx = _ctx(close_value=None, ma20_value=50000.0,
               rsi_prev_level=28.0, rsi_curr_level=36.0)
    score, _ = calculate_momentum_pivot_score(ctx, "KR")
    assert score == 0.0  # BR-01


# ── Supply/Demand ─────────────────────────────────────────────────────────────

def test_supply_demand_kr_positive_turn():
    ctx = _ctx(cumulative_net_buy_value=500.0, prev_cumulative_net_buy_value=-100.0)
    score, signals = calculate_supply_demand_score(ctx, "KR")
    assert score == 30.0
    assert "양전 전환" in signals[0]


def test_supply_demand_kr_already_positive():
    ctx = _ctx(cumulative_net_buy_value=500.0, prev_cumulative_net_buy_value=200.0)
    score, _ = calculate_supply_demand_score(ctx, "KR")
    assert score == 0.0  # 이미 양수 → 전환 아님


def test_supply_demand_us_always_zero():
    ctx = _ctx(market="US", cumulative_net_buy_value=500.0, prev_cumulative_net_buy_value=-100.0)
    score, _ = calculate_supply_demand_score(ctx, "US")
    assert score == 0.0


def test_supply_demand_prev_none_returns_zero():
    """전일 데이터 None → 데이터 부족으로 0점 (오작동 방지)"""
    ctx = _ctx(cumulative_net_buy_value=500.0, prev_cumulative_net_buy_value=None)
    score, _ = calculate_supply_demand_score(ctx, "KR")
    assert score == 0.0


def test_supply_demand_curr_none_returns_zero():
    ctx = _ctx(cumulative_net_buy_value=None, prev_cumulative_net_buy_value=-100.0)
    score, _ = calculate_supply_demand_score(ctx, "KR")
    assert score == 0.0


# ── 통합 스코어 ───────────────────────────────────────────────────────────────

def test_total_score_kr_full_pass():
    ctx = _ctx(
        pbr_value=0.55, pbr_min_value=0.5,
        close_value=55000.0, ma20_value=50000.0,
        rsi_prev_level=28.0, rsi_curr_level=36.0,
        cumulative_net_buy_value=500.0, prev_cumulative_net_buy_value=-100.0,
    )
    ks = KillSwitchResult(active=False)
    breakdown = calculate_total_score(ctx, "KR", ks)
    assert breakdown.total_score == 100.0
    assert breakdown.total_score >= ALERT_THRESHOLD


def test_total_score_kill_switch_forces_zero():
    ctx = _ctx(pbr_value=0.55, pbr_min_value=0.5,
               close_value=55000.0, ma20_value=50000.0,
               rsi_prev_level=28.0, rsi_curr_level=36.0)
    ks = KillSwitchResult(active=True, reason="VIX=35>30")
    breakdown = calculate_total_score(ctx, "KR", ks)
    assert breakdown.total_score == 0.0
    assert breakdown.kill_switch_active is True
