"""seed_migrator.py 단위 테스트"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from src.backtesting.seed_migrator import generate_pbr_stats


def _mock_ticker(book_value=1000.0, prices=None, has_balance_sheet=True):
    if prices is None:
        prices = [500.0 + i for i in range(100)]
    hist = pd.DataFrame(
        {"Close": prices},
        index=pd.bdate_range("2018-01-01", periods=len(prices))
    )
    mock_tk = MagicMock()
    mock_tk.history.return_value = hist
    mock_tk.info = {"bookValue": book_value}

    if has_balance_sheet:
        bs = pd.DataFrame(
            {"2025-12-31": [424313255000000.0, 6686083126.0]},
            index=["Stockholders Equity", "Ordinary Shares Number"]
        )
        # BPS = 424313255000000 / 6686083126 ≈ 63462
        mock_tk.quarterly_balance_sheet = bs
    else:
        mock_tk.quarterly_balance_sheet = pd.DataFrame()

    return mock_tk


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_pbr_min_is_raw_value_no_factor(mock_yf):
    """pbr_min_value는 순수 원본 값 — CONSERVATIVE_FACTOR 없음"""
    mock_yf.return_value = _mock_ticker(
        book_value=1000.0,
        prices=[400.0, 500.0, 600.0, 700.0] * 25,
        has_balance_sheet=False  # US 종목 시뮬레이션 — bookValue fallback
    )
    result = generate_pbr_stats("AAPL", "2018-01-01", "2025-01-01")
    assert result is not None
    raw_min = round(400.0 / 1000.0, 4)
    assert result.pbr_min_value == raw_min  # 0.4 그대로, 1.2 곱셈 없음


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_pbr_min_equals_actual_minimum(mock_yf):
    """pbr_min이 실제 최솟값과 동일"""
    mock_yf.return_value = _mock_ticker(
        book_value=500.0,
        prices=[200.0, 300.0, 400.0] * 33,
        has_balance_sheet=False
    )
    result = generate_pbr_stats("MSFT", "2018-01-01", "2025-01-01")
    assert result is not None
    raw_min = round(200.0 / 500.0, 4)
    assert result.pbr_min_value == raw_min


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_kr_uses_balance_sheet_bps(mock_yf):
    """KR 종목은 balance sheet에서 BPS 직접 계산"""
    mock_yf.return_value = _mock_ticker(has_balance_sheet=True)
    result = generate_pbr_stats("005930.KS", "2018-01-01", "2025-01-01")
    assert result is not None
    assert result.pbr_min_value > 0
    assert result.pbr_median_value > 0


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_missing_book_value_and_no_balance_sheet_returns_none(mock_yf):
    mock_tk = MagicMock()
    mock_tk.history.return_value = pd.DataFrame(
        {"Close": [100.0] * 50},
        index=pd.bdate_range("2020-01-01", periods=50)
    )
    mock_tk.info = {"bookValue": None}
    mock_tk.quarterly_balance_sheet = pd.DataFrame()
    mock_yf.return_value = mock_tk
    result = generate_pbr_stats("TEST", "2020-01-01", "2021-01-01")
    assert result is None


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_empty_history_returns_none(mock_yf):
    mock_tk = MagicMock()
    mock_tk.history.return_value = pd.DataFrame()
    mock_tk.info = {"bookValue": 1000.0}
    mock_tk.quarterly_balance_sheet = pd.DataFrame()
    mock_yf.return_value = mock_tk
    result = generate_pbr_stats("TEST", "2020-01-01", "2021-01-01")
    assert result is None
