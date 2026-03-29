"""seed_migrator.py 단위 테스트"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from src.backtesting.seed_migrator import generate_pbr_stats, CONSERVATIVE_FACTOR  # type: ignore


def _mock_ticker(book_value=1000.0, prices=None):
    if prices is None:
        prices = [500.0 + i for i in range(100)]
    hist = pd.DataFrame(
        {"Close": prices},
        index=pd.bdate_range("2018-01-01", periods=len(prices))
    )
    mock_tk = MagicMock()
    mock_tk.history.return_value = hist
    mock_tk.info = {"bookValue": book_value}
    return mock_tk


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_conservative_factor_applied(mock_yf):
    mock_yf.return_value = _mock_ticker(book_value=1000.0, prices=[400.0, 500.0, 600.0, 700.0] * 25)
    result = generate_pbr_stats("005930.KS", "2018-01-01", "2025-01-01")
    assert result is not None
    # raw_min = 400/1000 = 0.4 → conservative_min = 0.4 * 1.2 = 0.48
    raw_min = round(400.0 / 1000.0, 4)
    expected_min = round(raw_min * 1.2, 4)
    assert result.pbr_min_value == expected_min


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_pbr_min_higher_than_raw(mock_yf):
    """보수적 가중치로 pbr_min이 실제 최솟값보다 높음"""
    mock_yf.return_value = _mock_ticker(book_value=500.0, prices=[200.0, 300.0, 400.0] * 33)
    result = generate_pbr_stats("AAPL", "2018-01-01", "2025-01-01")
    assert result is not None
    raw_min = round(200.0 / 500.0, 4)
    assert result.pbr_min_value > raw_min


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_missing_book_value_returns_none(mock_yf):
    mock_tk = MagicMock()
    mock_tk.history.return_value = pd.DataFrame(
        {"Close": [100.0] * 50},
        index=pd.bdate_range("2020-01-01", periods=50)
    )
    mock_tk.info = {"bookValue": None}
    mock_yf.return_value = mock_tk
    result = generate_pbr_stats("TEST", "2020-01-01", "2021-01-01")
    assert result is None


@patch("src.backtesting.seed_migrator.yf.Ticker")
def test_empty_history_returns_none(mock_yf):
    mock_tk = MagicMock()
    mock_tk.history.return_value = pd.DataFrame()
    mock_tk.info = {"bookValue": 1000.0}
    mock_yf.return_value = mock_tk
    result = generate_pbr_stats("TEST", "2020-01-01", "2021-01-01")
    assert result is None
