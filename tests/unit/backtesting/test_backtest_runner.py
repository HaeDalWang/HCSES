"""Backtesting backtest_runner.py 단위 테스트"""
import pytest
import pandas as pd
import numpy as np
from datetime import date

from src.backtesting.backtest_runner import (
    calculate_forward_returns,
    simulate_scoring,
    export_report,
    AlertSignal,
)
from src.shared.scoring import ALERT_THRESHOLD


# ── 수익률 계산 ───────────────────────────────────────────────────────────────

def _make_price_df(n=200, start_price=100.0):
    """테스트용 가격 DataFrame 생성"""
    idx = pd.bdate_range("2021-01-01", periods=n)
    prices = [start_price * (1 + 0.001 * i) for i in range(n)]
    df = pd.DataFrame({
        "close_value": prices,
        "open_value": prices,
        "high_value": prices,
        "low_value": prices,
        "volume_value": [1000000] * n,
        "rsi_level": [35.0] * n,
        "ma20_value": [p * 0.95 for p in prices],
        "pbr_value": [0.5] * n,
        "pbr_min_rolling": [0.4] * n,
        "cum_net_buy_20d": [100.0] * n,
    }, index=idx)
    return df


def test_forward_returns_60d():
    df = _make_price_df(200)
    signal_date = df.index[10].strftime("%Y-%m-%d")
    returns = calculate_forward_returns(df, signal_date, [60, 90])
    assert returns[60] is not None
    assert isinstance(returns[60], float)


def test_forward_returns_insufficient_data():
    df = _make_price_df(30)
    signal_date = df.index[5].strftime("%Y-%m-%d")
    returns = calculate_forward_returns(df, signal_date, [60])
    assert returns[60] is None


def test_forward_returns_invalid_date():
    df = _make_price_df(100)
    returns = calculate_forward_returns(df, "1900-01-01", [60])
    assert returns[60] is None


# ── 스코어링 시뮬레이션 ───────────────────────────────────────────────────────

def test_simulate_scoring_no_signals_when_score_low():
    """PBR 조건 미충족 시 알람 없음"""
    df = _make_price_df(100)
    df["pbr_value"] = 2.0          # 높은 PBR → Valuation Floor 미충족
    df["pbr_min_rolling"] = 1.0
    df.attrs["ticker"] = "TEST"
    signals = simulate_scoring(df, "US")
    assert len(signals) == 0


def test_simulate_scoring_kill_switch_suppresses_signal():
    """Kill-Switch 활성 시 알람 없음"""
    df = _make_price_df(100)
    df["pbr_value"] = 0.4
    df["pbr_min_rolling"] = 0.4
    df.attrs["ticker"] = "TEST"
    # VIX > 30 → Kill-Switch 활성
    vix_df = pd.DataFrame(
        {"close_value": [35.0] * 100},
        index=df.index
    )
    signals = simulate_scoring(df, "US", vix_df=vix_df)
    assert len(signals) == 0


# ── 리포트 출력 ───────────────────────────────────────────────────────────────

def test_export_report_creates_csv(tmp_path):
    signals = [
        AlertSignal(
            ticker="005930.KS", market="KR", signal_date="2022-06-15",
            entry_price_value=60000.0, total_score=100.0,
            signals=["ValuationFloor", "MomentumPivot"],
            return_60d_pct=12.5, return_90d_pct=18.3, return_150d_pct=25.0,
        )
    ]
    output = str(tmp_path / "test_report.csv")
    export_report(signals, output)
    import csv
    with open(output) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["ticker"] == "005930.KS"
    assert rows[0]["return_60d_pct"] == "12.5"


def test_export_report_empty_signals(capsys):
    export_report([], "dummy.csv")
    captured = capsys.readouterr()
    assert "알람 발생 없음" in captured.out
