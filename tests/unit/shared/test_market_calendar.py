"""shared/market_calendar.py 단위 테스트"""
import pytest
from datetime import date, datetime
import pytz
from src.shared.market_calendar import is_market_holiday, is_dst_active, get_us_market_utc_open


def test_weekend_is_holiday():
    saturday = date(2026, 3, 28)
    assert is_market_holiday("KR", saturday) is True
    assert is_market_holiday("US", saturday) is True


def test_weekday_not_holiday():
    monday = date(2026, 3, 30)
    assert is_market_holiday("US", monday) is False


def test_kr_holiday():
    new_year = date(2026, 1, 1)
    assert is_market_holiday("KR", new_year) is True


def test_dst_active_in_summer():
    # 2026년 7월은 EDT (DST 활성)
    summer = datetime(2026, 7, 1, 12, 0)
    assert is_dst_active(summer) is True


def test_dst_inactive_in_winter():
    # 2026년 1월은 EST (DST 비활성)
    winter = datetime(2026, 1, 15, 12, 0)
    assert is_dst_active(winter) is False


def test_us_market_open_edt():
    summer = datetime(2026, 7, 1, 12, 0)
    assert get_us_market_utc_open(summer) == 13


def test_us_market_open_est():
    winter = datetime(2026, 1, 15, 12, 0)
    assert get_us_market_utc_open(winter) == 14
