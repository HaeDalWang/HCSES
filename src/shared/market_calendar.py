"""
시장 캘린더 유틸리티
- 공휴일/휴장일 판별
- DST 감지 (TC-04)
"""
import logging
from datetime import date, datetime
import pytz

logger = logging.getLogger(__name__)

# 한국 공휴일 (간소화 — 실운영 시 exchange_calendars 라이브러리 권장)
KR_HOLIDAYS_2024_2026 = {
    "2024-01-01", "2024-02-09", "2024-02-12", "2024-03-01",
    "2024-05-05", "2024-05-06", "2024-05-15", "2024-06-06",
    "2024-08-15", "2024-09-16", "2024-09-17", "2024-09-18",
    "2024-10-03", "2024-10-09", "2024-12-25",
    "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30",
    "2025-03-01", "2025-05-05", "2025-05-06", "2025-06-06",
    "2025-08-15", "2025-10-03", "2025-10-06", "2025-10-07",
    "2025-10-08", "2025-10-09", "2025-12-25",
    "2026-01-01", "2026-02-17", "2026-02-18", "2026-02-19",
    "2026-03-01", "2026-05-05", "2026-06-06", "2026-08-17",
    "2026-09-24", "2026-09-25", "2026-10-09", "2026-12-25",
}


def is_market_holiday(market: str, target_date: date) -> bool:
    """공휴일 또는 주말 여부 확인"""
    if target_date.weekday() >= 5:  # 토/일
        return True
    date_str = target_date.strftime("%Y-%m-%d")
    if market == "KR" and date_str in KR_HOLIDAYS_2024_2026:
        return True
    # US 공휴일은 yfinance가 빈 DataFrame 반환으로 처리
    return False


def is_dst_active(dt: datetime) -> bool:
    """미국 동부 시간 기준 DST 활성화 여부 (TC-04)"""
    eastern = pytz.timezone("America/New_York")
    aware = eastern.localize(dt.replace(tzinfo=None))
    return bool(aware.dst())


def get_us_market_utc_open(dt: datetime) -> int:
    """
    미국 장 시작 UTC 시간 반환 (시 단위)
    EDT(DST): 13:30 UTC / EST: 14:30 UTC
    """
    return 13 if is_dst_active(dt) else 14


def get_us_market_utc_close(dt: datetime) -> int:
    """미국 장 마감 UTC 시간 (시 단위). EDT: 20:00 / EST: 21:00"""
    return 20 if is_dst_active(dt) else 21


def is_within_market_hours(market: str, dt: datetime) -> bool:
    """현재 시각이 해당 시장 운영 시간 내인지 확인"""
    if market == "KR":
        kst = pytz.timezone("Asia/Seoul")
        local = dt.astimezone(kst)
        return 9 <= local.hour < 15 or (local.hour == 15 and local.minute <= 30)
    elif market == "US":
        open_h = get_us_market_utc_open(dt)
        close_h = get_us_market_utc_close(dt)
        utc = dt.astimezone(pytz.utc)
        return open_h <= utc.hour < close_h
    return False
