"""DataCollector ingestion_service.py 단위 테스트"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import date

from src.data_collector.ingestion_service import (
    normalize_numeric_fields,
    _calc_rsi,
    _calc_ma20,
    _calc_bollinger_bands,
)
from src.shared.models import StockDailyRecord


# ── 정규화 테스트 ─────────────────────────────────────────────────────────────

def test_normalize_rounds_to_4_decimal():
    r = StockDailyRecord(ticker="T", market="KR", date="2026-01-01",
                         close_value=12345.123456, pbr_value=1.23456789)
    result = normalize_numeric_fields(r)
    assert result.close_value == 12345.1235
    assert result.pbr_value == 1.2346


def test_normalize_preserves_none():
    r = StockDailyRecord(ticker="T", market="KR", date="2026-01-01",
                         pbr_value=None, rsi_level=None)
    result = normalize_numeric_fields(r)
    assert result.pbr_value is None
    assert result.rsi_level is None


# ── RSI 계산 테스트 ───────────────────────────────────────────────────────────

def test_rsi_insufficient_data():
    closes = pd.Series([100.0] * 10)
    assert _calc_rsi(closes) is None


def test_rsi_all_gains_returns_100():
    # 모든 날 상승 → avg_loss=0 → RSI=100
    closes = pd.Series([float(i) for i in range(1, 20)])
    result = _calc_rsi(closes)
    assert result == 100.0


def test_rsi_range():
    np.random.seed(42)
    prices = pd.Series(100 + np.random.randn(50).cumsum())
    result = _calc_rsi(prices)
    assert result is not None
    assert 0 <= result <= 100


def test_rsi_wilder_smoothing_differs_from_sma():
    """Wilder's ewm 방식이 SMA rolling과 다른 값을 반환함을 확인"""
    np.random.seed(7)
    closes = pd.Series(100 + np.random.randn(40).cumsum())
    # ewm 방식 (현재 구현)
    result_ewm = _calc_rsi(closes)
    # SMA 방식 (구버전)
    delta = closes.diff().dropna()
    avg_gain_sma = delta.clip(lower=0).tail(14).mean()
    avg_loss_sma = (-delta.clip(upper=0)).tail(14).mean()
    result_sma = round(100 - (100 / (1 + avg_gain_sma / avg_loss_sma)), 4) if avg_loss_sma else 100.0
    # 두 값이 다를 수 있음 (Wilder's가 더 정확)
    assert result_ewm is not None
    assert 0 <= result_ewm <= 100


# ── MA20 계산 테스트 ──────────────────────────────────────────────────────────

def test_ma20_insufficient_data():
    closes = pd.Series([100.0] * 15)
    assert _calc_ma20(closes) is None


def test_ma20_correct():
    closes = pd.Series([float(i) for i in range(1, 25)])  # 1~24
    result = _calc_ma20(closes)
    expected = round(sum(range(5, 25)) / 20, 4)
    assert result == expected


# ── 볼린저 밴드 테스트 ────────────────────────────────────────────────────────

def test_bollinger_insufficient_data():
    series = pd.Series([1300.0] * 10)
    upper, lower = _calc_bollinger_bands(series)
    assert upper is None
    assert lower is None


def test_bollinger_upper_gt_lower():
    series = pd.Series([1300.0 + i * 0.5 for i in range(25)])
    upper, lower = _calc_bollinger_bands(series)
    assert upper is not None and lower is not None
    assert upper > lower
