"""
HCSES 스코어링 로직 (공유 모듈)
Unit 2 (QuantAnalyzer) 및 Unit 4 (Backtesting) 공통 사용
EC-02: 절대값(_value, _level) vs 변동률(_pct) 접미사 규칙 적용
보수적 원칙: 조건 모호 또는 데이터 결측 시 False(0점) 반환
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ── 가중치 상수 ───────────────────────────────────────────────────────────────
KR_WEIGHTS = {"valuation": 40, "momentum": 30, "supply_demand": 30}
US_WEIGHTS = {"valuation": 60, "momentum": 40, "supply_demand": 0}

ALERT_THRESHOLD = 90.0


@dataclass
class KillSwitchResult:
    active: bool
    reason: str = ""
    vix_value: Optional[float] = None
    yield_change_pct: Optional[float] = None
    krwusd_value: Optional[float] = None
    krwusd_bb_upper_value: Optional[float] = None


@dataclass
class ScoringContext:
    ticker: str
    market: str
    date: str
    # Valuation
    pbr_value: Optional[float] = None
    pbr_min_value: Optional[float] = None
    # Momentum
    close_value: Optional[float] = None
    ma20_value: Optional[float] = None
    rsi_prev_level: Optional[float] = None
    rsi_curr_level: Optional[float] = None
    # Supply/Demand (KR only)
    cumulative_net_buy_value: Optional[float] = None
    prev_cumulative_net_buy_value: Optional[float] = None


@dataclass
class ScoreBreakdown:
    ticker: str
    market: str
    date: str
    valuation_score: float = 0.0
    momentum_score: float = 0.0
    supply_demand_score: float = 0.0
    total_score: float = 0.0
    kill_switch_active: bool = False
    kill_switch_reason: str = ""
    signals: list = field(default_factory=list)


# ── Kill-Switch ───────────────────────────────────────────────────────────────

def evaluate_kill_switch(indicators: dict) -> KillSwitchResult:
    """
    Kill-Switch 3단계 평가:
    - VIX > 30 (stale: > 27): score 강제 0
    - 25 < VIX <= 30 (stale: 23 < VIX <= 27): 경고 (차단 아님)
    - US10Y change_pct > 3% (stale: > 2%): score 강제 0
    - KRWUSD > 볼린저 상단: score 강제 0
    """
    warning_reason = ""

    # VIX
    vix_data = indicators.get("VIX", {})
    vix_value = vix_data.get("value_value")
    is_stale = bool(vix_data.get("stale"))

    if vix_value is not None:
        vix_f = float(vix_value)
        kill_threshold = 27.0 if is_stale else 30.0
        warn_threshold = 23.0 if is_stale else 25.0

        if vix_f > kill_threshold:
            return KillSwitchResult(
                active=True,
                reason=f"VIX={vix_f}>{kill_threshold}{'(stale)' if is_stale else ''}",
                vix_value=vix_f)
        elif vix_f > warn_threshold:
            warning_reason = f"⚠️ VIX={vix_f} (경고 구간{'·stale' if is_stale else ''})"

    # US10Y
    yield_data = indicators.get("US10Y", {})
    yield_change_pct = yield_data.get("change_pct")
    yield_stale = bool(yield_data.get("stale"))
    yield_threshold = 2.0 if yield_stale else 3.0

    if yield_change_pct is not None and float(yield_change_pct) > yield_threshold:
        return KillSwitchResult(
            active=True,
            reason=f"US10Y_change_pct={yield_change_pct}>{yield_threshold}"
                   f"{'(stale)' if yield_stale else ''}",
            yield_change_pct=float(yield_change_pct))

    # KRWUSD
    krw_data = indicators.get("KRWUSD", {})
    krwusd_value = krw_data.get("value_value")
    bb_upper_value = krw_data.get("bb_upper_value")
    if (krwusd_value is not None and bb_upper_value is not None and
            float(krwusd_value) > float(bb_upper_value)):
        return KillSwitchResult(
            active=True,
            reason=f"KRWUSD={krwusd_value}>BB_upper={bb_upper_value}"
                   f"{'(stale)' if krw_data.get('stale') else ''}",
            krwusd_value=float(krwusd_value),
            krwusd_bb_upper_value=float(bb_upper_value))

    # 경고 구간 (차단 아님)
    return KillSwitchResult(active=False, reason=warning_reason)


# ── 개별 스코어링 함수 ────────────────────────────────────────────────────────

def calculate_valuation_floor_score(ctx: ScoringContext, market: str) -> tuple[float, list]:
    """BR-03: PBR <= Min(PBR) * 1.1"""
    signals = []
    if ctx.pbr_value is None or ctx.pbr_min_value is None:
        return 0.0, signals  # BR-01 보수적 원칙
    threshold_value = round(ctx.pbr_min_value * 1.1, 4)
    if ctx.pbr_value <= threshold_value:
        weights = KR_WEIGHTS if market == "KR" else US_WEIGHTS
        score = float(weights["valuation"])
        signals.append(
            f"ValuationFloor: PBR({ctx.pbr_value}) <= MinPBR*1.1({threshold_value})"
        )
        return score, signals
    return 0.0, signals


def calculate_momentum_pivot_score(ctx: ScoringContext, market: str) -> tuple[float, list]:
    """BR-04: Price>MA20 AND RSI 30→35 돌파"""
    signals = []
    if any(v is None for v in [ctx.close_value, ctx.ma20_value,
                                ctx.rsi_prev_level, ctx.rsi_curr_level]):
        return 0.0, signals  # BR-01
    if (ctx.close_value > ctx.ma20_value and          # type: ignore[operator]
            ctx.rsi_prev_level <= 30 and               # type: ignore[operator]
            ctx.rsi_curr_level > 35):                  # type: ignore[operator]
        weights = KR_WEIGHTS if market == "KR" else US_WEIGHTS
        score = float(weights["momentum"])
        signals.append(
            f"MomentumPivot: Price({ctx.close_value})>MA20({ctx.ma20_value}), "
            f"RSI {ctx.rsi_prev_level}→{ctx.rsi_curr_level}"
        )
        return score, signals
    return 0.0, signals


def calculate_supply_demand_score(ctx: ScoringContext, market: str) -> tuple[float, list]:
    """BR-05: 외국인+기관 20거래일 누적 순매수합 양전 전환 (KR only)"""
    signals = []
    if market != "KR":
        return 0.0, signals
    # 전일 데이터 None은 명시적으로 0점 처리 (데이터 부족에 의한 오작동 방지)
    if ctx.cumulative_net_buy_value is None or ctx.prev_cumulative_net_buy_value is None:
        return 0.0, signals  # BR-01
    # 양전 전환: 전일 ≤ 0 → 당일 > 0 (두 값 모두 유효한 경우에만 판단)
    if (ctx.cumulative_net_buy_value > 0 and
            ctx.prev_cumulative_net_buy_value <= 0):
        signals.append(
            f"SupplyDemand: CumNetBuy {ctx.prev_cumulative_net_buy_value}"
            f"→{ctx.cumulative_net_buy_value} (양전 전환)"
        )
        return 30.0, signals
    return 0.0, signals


# ── 통합 스코어 계산 ──────────────────────────────────────────────────────────

def calculate_total_score(
    ctx: ScoringContext,
    market: str,
    kill_switch: KillSwitchResult,
) -> ScoreBreakdown:
    """전체 스코어 산출. Kill-Switch 활성 시 0점 강제."""
    breakdown = ScoreBreakdown(ticker=ctx.ticker, market=market, date=ctx.date)

    if kill_switch.active:
        breakdown.kill_switch_active = True
        breakdown.kill_switch_reason = kill_switch.reason
        breakdown.total_score = 0.0
        return breakdown

    v_score, v_signals = calculate_valuation_floor_score(ctx, market)
    m_score, m_signals = calculate_momentum_pivot_score(ctx, market)
    s_score, s_signals = calculate_supply_demand_score(ctx, market)

    breakdown.valuation_score = v_score
    breakdown.momentum_score = m_score
    breakdown.supply_demand_score = s_score
    breakdown.total_score = round(v_score + m_score + s_score, 4)
    breakdown.signals = v_signals + m_signals + s_signals
    return breakdown
