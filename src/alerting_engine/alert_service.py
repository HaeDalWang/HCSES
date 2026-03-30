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
    """BR-02: 손절가 = 현재가 × (PBR Min / 현재 PBR)"""
    if not pbr_value or pbr_value == 0 or pbr_min_value is None:
        return "N/A"
    raw = current_price_value * (pbr_min_value / pbr_value)
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

def format_alert_message(
    ticker: str,
    ticker_name: str,
    market: str,
    date: str,
    current_price_value: float,
    target_price_str: str,
    stop_loss_price_str: str,
    breakdown: dict,
) -> str:
    """BR-01: 알람 메시지 포맷 생성"""
    currency = "₩" if market == "KR" else "$"
    price_fmt = _format_price(current_price_value, market)
    target_pct = _pct_change(current_price_value, target_price_str)
    stop_pct = _pct_change(current_price_value, stop_loss_price_str)

    signals = breakdown.get("signals", [])
    signals_text = "\n".join(f"  • {s}" for s in signals) if signals else "  • (없음)"

    # 종목명과 티커를 함께 표시 (KR: "삼성전자 (005930.KS)", US: "Apple (AAPL)")
    title = f"{ticker_name} ({ticker})" if ticker_name != ticker else ticker

    lines = [
        f"🚨 [HCSES 알람] {title} · {market}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"현재가:   {currency}{price_fmt}",
        f"목표가:   {currency}{target_price_str}  ({target_pct})",
        f"손절가:   {currency}{stop_loss_price_str}  ({stop_pct})",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📊 스코어: {breakdown.get('total_score', 0)} / 100",
        f"  • Valuation Floor: {breakdown.get('valuation_score', 0)}점",
        f"  • Momentum Pivot:  {breakdown.get('momentum_score', 0)}점",
        f"  • Supply/Demand:   {breakdown.get('supply_demand_score', 0)}점",
        "━━━━━━━━━━━━━━━━━━━━",
        "🔍 감지된 시그널:",
        signals_text,
        "━━━━━━━━━━━━━━━━━━━━",
        f"📅 {date}",
    ]
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
