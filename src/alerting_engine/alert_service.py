"""
AlertingEngine 알람 서비스
FR-05, BR-01~06, TC-02, TC-03
"""
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DISCORD_CHAR_LIMIT = 2000


# ── 가격 포맷 ─────────────────────────────────────────────────────────────────

def _format_price(value: float, market: str) -> str:
    """
    시장별 가격 포맷:
    - KR: 천 단위 콤마, 소수점 없음  (예: 75,000)
    - US: 천 단위 콤마, 소수점 2자리 (예: 182.45)
    """
    if market == "KR":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


# ── 가격 계산 ─────────────────────────────────────────────────────────────────

def calc_target_price(
    current_price_value: float,
    pbr_median_value: Optional[float],
    pbr_value: Optional[float],
    market: str = "KR",
) -> str:
    """BR-02: 목표가 = 현재가 × (PBR Median / 현재 PBR)"""
    if not pbr_value or pbr_value == 0 or pbr_median_value is None:
        return "N/A"
    raw = current_price_value * (pbr_median_value / pbr_value)
    return _format_price(raw, market)


def calc_stop_loss_price(
    current_price_value: float,
    pbr_min_value: Optional[float],
    pbr_value: Optional[float],
    market: str = "KR",
) -> str:
    """손절가 = 현재가 × (PBR Min / 현재 PBR) — 레거시, ATR 방식으로 대체됨"""
    if not pbr_value or pbr_value == 0 or pbr_min_value is None:
        return "N/A"
    raw = current_price_value * (pbr_min_value / pbr_value)
    return _format_price(raw, market)


def calc_stop_loss_atr(
    current_price_value: float,
    atr_value: Optional[float],
    market: str = "KR",
    multiplier: float = 2.0,
) -> str:
    """
    손절가 = 현재가 - (ATR(14) × 2.0)
    ATR 없으면 N/A (보수적 원칙).
    """
    if atr_value is None or atr_value <= 0:
        return "N/A"
    raw = current_price_value - (atr_value * multiplier)
    if raw <= 0:
        return "N/A"
    return _format_price(raw, market)


def _pct_change(current: float, target_str: str) -> str:
    try:
        target = float(target_str.replace(",", ""))
        pct = (target - current) / current * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.1f}%"
    except (ValueError, ZeroDivisionError):
        return ""


# ── 메시지 포맷 ───────────────────────────────────────────────────────────────

def calc_partial_exit(target_price_str: str, market: str = "KR") -> str:
    """1차 익절가 = 목표가의 70%"""
    try:
        target = float(target_price_str.replace(",", ""))
        raw = target * 0.7
        return _format_price(raw, market)
    except (ValueError, TypeError):
        return "N/A"


def format_alert_message(
    ticker: str,
    ticker_name: str,
    market: str,
    date: str,
    current_price_value: float,
    target_price_str: str,
    stop_loss_price_str: str,
    breakdown: dict,
    atr_value: Optional[float] = None,
    pbr_value: Optional[float] = None,
    pbr_min_value: Optional[float] = None,
    pbr_median_value: Optional[float] = None,
    vix_value: Optional[float] = None,
    us10y_value: Optional[float] = None,
    kill_switch_warning: str = "",
) -> str:
    """plan-v1.0.md 섹션 5 포맷 준수"""
    currency = "₩" if market == "KR" else "$"
    price_fmt = _format_price(current_price_value, market)
    target_pct = _pct_change(current_price_value, target_price_str)
    stop_pct = _pct_change(current_price_value, stop_loss_price_str)

    partial_str = calc_partial_exit(target_price_str, market)
    partial_pct = _pct_change(current_price_value, partial_str)

    title = f"{ticker_name} ({ticker})" if ticker_name != ticker else ticker
    score = breakdown.get("total_score", 0)
    v_score = breakdown.get("valuation_score", 0)
    m_score = breakdown.get("momentum_score", 0)
    rsi_prev = breakdown.get("rsi_prev_level", "?")
    rsi_curr = breakdown.get("rsi_curr_level", "?")

    atr_fmt = _format_price(atr_value, market) if atr_value else "N/A"
    pbr_fmt = f"{pbr_value:.2f}x" if pbr_value else "N/A"
    pbr_min_fmt = f"{pbr_min_value:.2f}x" if pbr_min_value else "N/A"
    pbr_med_fmt = f"{pbr_median_value:.2f}x" if pbr_median_value else "N/A"
    vix_fmt = f"{vix_value:.1f}" if vix_value else "N/A"
    us10y_fmt = f"{us10y_value:.2f}%" if us10y_value else "N/A"

    lines = [
        f"🚨 매수 신호 | {title} | {market}",
        "",
        "━━━━━━━━ 진입 근거 ━━━━━━━━",
        f"현재가:         {currency}{price_fmt}",
        f"HCSES 점수:     {score} / 100",
        f"  └ Valuation:  {v_score} (PBR Floor {'충족' if v_score > 0 else '미충족'})",
        f"  └ Momentum:   {m_score} (RSI {rsi_prev}→{rsi_curr} 돌파)",
        "",
        f"PBR 현재:       {pbr_fmt}",
        f"PBR 역사 최저:  {pbr_min_fmt}",
        f"PBR 중앙값:     {pbr_med_fmt}",
        "",
        "━━━━━━━━ 출구 전략 ━━━━━━━━",
        f"ATR(14):        {currency}{atr_fmt}",
        f"손절가:  {currency}{stop_loss_price_str}  (현재가 - 2×ATR)   → {stop_pct}",
        f"1차익절: {currency}{partial_str}  (목표가의 70%)     → {partial_pct}",
        f"목표가:  {currency}{target_price_str}  (PBR 중앙값 기준)  → {target_pct}",
        "타임컷:  매수일로부터 60일 내 미달성 시 전량 매도",
        "",
        "━━━━━━━━ 시장 상태 ━━━━━━━━",
        f"VIX:     {vix_fmt}",
        f"US10Y:   {us10y_fmt}",
        f"신호일:  {date}",
    ]

    if kill_switch_warning:
        lines.append(kill_switch_warning)

    if market == "KR":
        lines.append("※ 한국 시장 수급 지표는 전일 마감 기준")

    return "\n".join(lines)


def truncate_if_needed(message: str, limit: int = DISCORD_CHAR_LIMIT) -> str:
    """BR-03: Discord 2,000자 제한 초과 시 요약 버전으로 대체"""
    if len(message) <= limit:
        return message
    logger.warning(f"message_truncated original_len={len(message)} limit={limit}")
    lines = message.split("\n")
    summary_lines = [l for l in lines if any(
        kw in l for kw in ["알람", "스코어", "현재가", "📅"]
    )]
    summary = "\n".join(summary_lines)
    if len(summary) > limit:
        summary = summary[:limit - 3] + "..."
    return summary


# ── Discord 발송 ──────────────────────────────────────────────────────────────

def send_discord_alert(webhook_url: str, message: str) -> bool:
    """
    BR-05: 최대 3회 재시도 (지수 백오프)
    BR-06: webhook_url 로그 출력 금지 (SECURITY-03)
    """
    payload = {"content": message}
    for attempt in range(3):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                logger.info(f"discord_alert_sent attempt={attempt + 1}")
                return True
            logger.warning(f"discord_alert_failed status={resp.status_code} attempt={attempt + 1}")
        except requests.RequestException as e:
            logger.warning(f"discord_request_error attempt={attempt + 1} error={str(e)}")
        if attempt < 2:
            time.sleep(2 ** attempt)
    logger.error("discord_alert_all_retries_failed")
    return False
