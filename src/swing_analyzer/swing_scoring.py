"""
Tier 2 Swing 스코어링 로직
- 기술적 반등 초기 (40점)
- 가격 지지 확인 (30점)
- 거래량 확인 (30점)
Alert Threshold: 70점
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

SWING_ALERT_THRESHOLD = 70.0
VIX_PENALTY_LOWER = 25.0
VIX_PENALTY_UPPER = 30.0
VIX_PENALTY_FACTOR = 0.7

MAX_DAILY_ALERTS = 3
COOLDOWN_DAYS = 10


@dataclass
class SwingContext:
    ticker: str
    market: str
    date: str
    # 가격
    close_value: Optional[float] = None
    close_prev_value: Optional[float] = None
    low_prev_value: Optional[float] = None
    # 이동평균
    ma5_value: Optional[float] = None
    ma5_prev_value: Optional[float] = None
    ma20_value: Optional[float] = None
    # RSI
    rsi_curr_level: Optional[float] = None
    rsi_prev_level: Optional[float] = None
    rsi_prev_prev_level: Optional[float] = None
    # 볼린저 밴드
    bb_lower_value: Optional[float] = None
    # 거래량
    volume_value: Optional[int] = None
    volume_ma20_value: Optional[float] = None
    # 수급 (KR only)
    foreign_net_buy_value: Optional[float] = None
    institution_net_buy_value: Optional[float] = None
    # ATR
    atr_value: Optional[float] = None


@dataclass
class SwingBreakdown:
    ticker: str
    market: str
    date: str
    technical_rebound_score: float = 0.0
    price_support_score: float = 0.0
    volume_confirm_score: float = 0.0
    total_score: float = 0.0
    vix_penalty_applied: bool = False
    signals: list = field(default_factory=list)


def calculate_technical_rebound(ctx: SwingContext) -> tuple[float, list]:
    """조건 1: 기술적 반등 초기 (40점)"""
    signals = []

    # 조건 A: RSI 과매도 탈출 (35 이하 → 35 초과)
    if ctx.rsi_prev_level is not None and ctx.rsi_curr_level is not None:
        if ctx.rsi_prev_level <= 35 and ctx.rsi_curr_level > 35:
            signals.append(
                f"RSI 과매도 탈출: {ctx.rsi_prev_level:.1f}→{ctx.rsi_curr_level:.1f}"
            )
            return 40.0, signals

    # 조건 B: RSI 바닥 반등 (2일 연속 상승, 아직 40 이하)
    if (ctx.rsi_curr_level is not None and
            ctx.rsi_prev_level is not None and
            ctx.rsi_prev_prev_level is not None):
        if (ctx.rsi_curr_level < 40 and
                ctx.rsi_curr_level > ctx.rsi_prev_level and
                ctx.rsi_prev_level > ctx.rsi_prev_prev_level):
            signals.append(
                f"RSI 바닥 반등: {ctx.rsi_prev_prev_level:.1f}→"
                f"{ctx.rsi_prev_level:.1f}→{ctx.rsi_curr_level:.1f}"
            )
            return 40.0, signals

    return 0.0, signals


def calculate_price_support(ctx: SwingContext) -> tuple[float, list]:
    """조건 2: 가격 지지 확인 (30점)"""
    signals = []

    # 조건 A: 볼린저 하단 반등
    if (ctx.low_prev_value is not None and
            ctx.bb_lower_value is not None and
            ctx.close_value is not None):
        if (ctx.low_prev_value <= ctx.bb_lower_value and
                ctx.close_value > ctx.bb_lower_value):
            signals.append(
                f"볼린저 하단 반등: Low({ctx.low_prev_value:.2f})≤BB({ctx.bb_lower_value:.2f}), "
                f"Close({ctx.close_value:.2f})>BB"
            )
            return 30.0, signals

    # 조건 B: 단기 이평 회복 (MA5 돌파, MA20 아래)
    if (ctx.close_prev_value is not None and
            ctx.close_value is not None and
            ctx.ma5_value is not None and
            ctx.ma5_prev_value is not None and
            ctx.ma20_value is not None):
        if (ctx.close_prev_value < ctx.ma5_prev_value and
                ctx.close_value > ctx.ma5_value and
                ctx.close_value < ctx.ma20_value):
            signals.append(
                f"MA5 돌파: Close({ctx.close_value:.2f})>MA5({ctx.ma5_value:.2f}), "
                f"<MA20({ctx.ma20_value:.2f})"
            )
            return 30.0, signals

    return 0.0, signals


def calculate_volume_confirm(ctx: SwingContext) -> tuple[float, list]:
    """조건 3: 거래량 확인 (30점)"""
    signals = []

    # 거래량 서프라이즈
    if (ctx.volume_value is not None and
            ctx.volume_ma20_value is not None and
            ctx.volume_ma20_value > 0):
        volume_ratio = ctx.volume_value / ctx.volume_ma20_value
        if volume_ratio >= 1.5:
            signals.append(f"거래량 서프라이즈: {volume_ratio:.1f}x (≥1.5x)")
            return 30.0, signals

    # KR 추가: 외인+기관 동시 순매수
    if ctx.market == "KR":
        if (ctx.foreign_net_buy_value is not None and
                ctx.institution_net_buy_value is not None and
                ctx.foreign_net_buy_value > 0 and
                ctx.institution_net_buy_value > 0):
            signals.append(
                f"외인+기관 동시 순매수: 외인={ctx.foreign_net_buy_value:+.0f}, "
                f"기관={ctx.institution_net_buy_value:+.0f}"
            )
            return 30.0, signals

    return 0.0, signals


def calculate_swing_score(
    ctx: SwingContext,
    vix_value: Optional[float] = None,
) -> SwingBreakdown:
    """Tier 2 전체 스코어 산출. VIX 25~30 시 0.7 패널티."""
    breakdown = SwingBreakdown(ticker=ctx.ticker, market=ctx.market, date=ctx.date)

    t_score, t_signals = calculate_technical_rebound(ctx)
    p_score, p_signals = calculate_price_support(ctx)
    v_score, v_signals = calculate_volume_confirm(ctx)

    breakdown.technical_rebound_score = t_score
    breakdown.price_support_score = p_score
    breakdown.volume_confirm_score = v_score
    breakdown.signals = t_signals + p_signals + v_signals

    raw_total = t_score + p_score + v_score

    # VIX 패널티
    if vix_value is not None and VIX_PENALTY_LOWER < vix_value <= VIX_PENALTY_UPPER:
        raw_total = raw_total * VIX_PENALTY_FACTOR
        breakdown.vix_penalty_applied = True

    breakdown.total_score = round(raw_total, 4)
    return breakdown
