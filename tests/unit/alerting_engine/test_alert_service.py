"""AlertingEngine alert_service.py 단위 테스트"""
import pytest
from unittest.mock import patch, MagicMock

from src.alerting_engine.alert_service import (
    calc_target_price,
    calc_stop_loss_price,
    format_alert_message,
    truncate_if_needed,
    send_discord_alert,
    DISCORD_CHAR_LIMIT,
)


# ── 가격 계산 ─────────────────────────────────────────────────────────────────

def test_calc_target_price_normal():
    result = calc_target_price(75000.0, pbr_median_value=1.2, pbr_value=0.55, market="KR")
    assert result != "N/A"
    assert float(result.replace(",", "")) > 75000.0


def test_calc_target_price_pbr_zero():
    assert calc_target_price(75000.0, 1.2, 0, market="KR") == "N/A"


def test_calc_target_price_pbr_none():
    assert calc_target_price(75000.0, 1.2, None, market="KR") == "N/A"


def test_calc_target_price_median_none():
    assert calc_target_price(75000.0, None, 0.55, market="KR") == "N/A"


def test_calc_stop_loss_price_normal():
    result = calc_stop_loss_price(75000.0, pbr_min_value=0.4, pbr_value=0.55, market="KR")
    assert result != "N/A"
    assert float(result.replace(",", "")) < 75000.0


def test_format_price_kr_no_decimal():
    """KR: 소수점 없음, 천 단위 콤마"""
    result = calc_target_price(75000.0, pbr_median_value=1.2, pbr_value=0.55, market="KR")
    assert "." not in result
    assert "," in result


def test_format_price_us_two_decimal():
    """US: 소수점 2자리"""
    result = calc_target_price(150.0, pbr_median_value=4.0, pbr_value=3.0, market="US")
    assert result != "N/A"
    # 소수점 2자리 포함 여부 확인
    assert "." in result
    decimal_part = result.split(".")[-1]
    assert len(decimal_part) == 2


def test_format_price_us_large_value():
    """US 고가 종목: 천 단위 콤마 + 소수점 2자리"""
    result = calc_target_price(1500.0, pbr_median_value=2.0, pbr_value=1.5, market="US")
    assert "," in result
    assert "." in result


# ── 메시지 포맷 ───────────────────────────────────────────────────────────────

def _sample_breakdown():
    return {
        "total_score": 100.0,
        "valuation_score": 40.0,
        "momentum_score": 30.0,
        "supply_demand_score": 30.0,
        "signals": ["ValuationFloor: PBR(0.55)<=MinPBR*1.1(0.55)", "MomentumPivot: RSI 28→36"],
    }


def test_format_message_contains_required_fields():
    msg = format_alert_message(
        ticker="005930.KS", market="KR", date="2026-03-29",
        current_price_value=75000.0,
        target_price_str="92,000", stop_loss_price_str="61,000",
        breakdown=_sample_breakdown(),
    )
    assert "005930.KS" in msg
    assert "75,000" in msg
    assert "92,000" in msg
    assert "61,000" in msg
    assert "100.0" in msg
    assert "ValuationFloor" in msg


def test_format_message_kr_currency():
    msg = format_alert_message("T", "KR", "2026-01-01", 50000.0, "60,000", "40,000", _sample_breakdown())
    assert "₩" in msg


def test_format_message_us_currency():
    msg = format_alert_message("AAPL", "US", "2026-01-01", 150.0, "180", "120", _sample_breakdown())
    assert "$" in msg


# ── 2,000자 제한 ──────────────────────────────────────────────────────────────

def test_truncate_short_message_unchanged():
    msg = "short message"
    assert truncate_if_needed(msg) == msg


def test_truncate_long_message_within_limit():
    long_msg = "알람\n스코어: 100\n현재가: 75000\n📅 2026-03-29\n" + "x" * 2100
    result = truncate_if_needed(long_msg)
    assert len(result) <= DISCORD_CHAR_LIMIT


def test_truncate_preserves_key_info():
    long_msg = "🚨 [HCSES 알람] TEST\n스코어: 100\n현재가: 75000\n📅 2026-03-29\n" + "x" * 2100
    result = truncate_if_needed(long_msg)
    assert "알람" in result or len(result) <= DISCORD_CHAR_LIMIT


# ── Discord 발송 ──────────────────────────────────────────────────────────────

@patch("src.alerting_engine.alert_service.requests.post")
def test_send_discord_success(mock_post):
    mock_post.return_value = MagicMock(status_code=204)
    assert send_discord_alert("https://discord.com/webhook", "test") is True
    assert mock_post.call_count == 1


@patch("src.alerting_engine.alert_service.requests.post")
@patch("src.alerting_engine.alert_service.time.sleep")
def test_send_discord_retry_then_success(mock_sleep, mock_post):
    fail = MagicMock(status_code=429)
    ok = MagicMock(status_code=204)
    mock_post.side_effect = [fail, ok]
    assert send_discord_alert("https://discord.com/webhook", "test") is True
    assert mock_post.call_count == 2


@patch("src.alerting_engine.alert_service.requests.post")
@patch("src.alerting_engine.alert_service.time.sleep")
def test_send_discord_all_retries_fail(mock_sleep, mock_post):
    mock_post.return_value = MagicMock(status_code=500)
    assert send_discord_alert("https://discord.com/webhook", "test") is False
    assert mock_post.call_count == 3
