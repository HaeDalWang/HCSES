"""
HCSES Backtesting Runner
FR-06, BR-01~06
Look-ahead bias 방지: rolling PBR min 사용
"""
import argparse
import csv
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from src.shared.scoring import (
    ScoringContext, KillSwitchResult,
    evaluate_kill_switch, calculate_total_score, ALERT_THRESHOLD,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class AlertSignal:
    ticker: str
    market: str
    signal_date: str
    entry_price_value: float
    total_score: float
    signals: list = field(default_factory=list)
    return_60d_pct: Optional[float] = None
    return_90d_pct: Optional[float] = None
    return_150d_pct: Optional[float] = None


# ── 데이터 로드 ───────────────────────────────────────────────────────────────

def _fetch_pbr_history_fdr(ticker: str, start: str, end: str) -> Optional[pd.Series]:
    """EC-01: FDR 로컬 캐시 fallback (KR 종목 PBR 결측 시)"""
    try:
        import FinanceDataReader as fdr
        code = ticker.replace(".KS", "").replace(".KQ", "")
        cache_dir = os.path.expanduser("~/.fdr_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"{code}_pbr.parquet")

        if os.path.exists(cache_path):
            df = pd.read_parquet(cache_path)
        else:
            df = fdr.DataReader(code, start, end)
            if not df.empty:
                df.to_parquet(cache_path)

        if not df.empty and "PBR" in df.columns:
            return df["PBR"].dropna()
    except Exception as e:
        logger.warning(f"fdr_pbr_cache_failed ticker={ticker} error={str(e)}")
    return None


def load_historical_data(
    ticker: str, market: str, start: str, end: str
) -> Optional[pd.DataFrame]:
    """
    BR-02: yfinance Adjusted Close + PBR 히스토리컬 로드
    KR PBR 결측 시 FDR 로컬 캐시 fallback
    """
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=True,
                         progress=False, threads=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.rename(columns={
            "Open": "open_value", "High": "high_value", "Low": "low_value",
            "Close": "close_value", "Volume": "volume_value",
        })

        # RSI(14) — Wilder's Smoothing (ewm, alpha=1/14)
        # SMA rolling(14).mean() 대신 표준 지수 평활화 사용
        # 짧은 데이터셋에서 SMA와 오차 발생 방지
        delta = df["close_value"].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi_level"] = (100 - 100 / (1 + rs)).round(4)

        # MA20
        df["ma20_value"] = df["close_value"].rolling(20).mean().round(4)

        # PBR (yfinance info — 단일 값, 히스토리컬 근사)
        pbr_series = None
        try:
            info = yf.Ticker(ticker).info
            book_value = info.get("bookValue")
            if book_value and float(book_value) > 0:
                pbr_series = (df["close_value"] / float(book_value)).round(4)
        except Exception:
            pass

        # KR PBR 결측 시 FDR fallback
        if pbr_series is None and market == "KR":
            fdr_pbr = _fetch_pbr_history_fdr(ticker, start, end)
            if fdr_pbr is not None:
                pbr_series = fdr_pbr.reindex(df.index).ffill()

        df["pbr_value"] = pbr_series if pbr_series is not None else np.nan

        # Look-ahead bias 방지: rolling min PBR
        df["pbr_min_rolling"] = df["pbr_value"].expanding().min().round(4)

        # KR 수급: FDR에서 외국인+기관 순매수 로드
        if market == "KR":
            try:
                import FinanceDataReader as fdr
                code = ticker.replace(".KS", "").replace(".KQ", "")
                inv_df = fdr.DataReader(code, start, end)
                if not inv_df.empty:
                    f_col = next((c for c in inv_df.columns if "외국인" in c or "Foreign" in c), None)
                    i_col = next((c for c in inv_df.columns if "기관" in c or "Institution" in c), None)
                    if f_col and i_col:
                        df["net_buy_daily"] = (
                            inv_df[f_col].reindex(df.index).fillna(0) +
                            inv_df[i_col].reindex(df.index).fillna(0)
                        )
                        df["cum_net_buy_20d"] = df["net_buy_daily"].rolling(20).sum().round(4)
            except Exception as e:
                logger.warning(f"supply_demand_load_failed ticker={ticker} error={str(e)}")
                df["cum_net_buy_20d"] = np.nan
        else:
            df["cum_net_buy_20d"] = np.nan

        # 소수점 4자리 정규화
        for col in ["open_value", "high_value", "low_value", "close_value"]:
            df[col] = df[col].round(4)

        return df.dropna(subset=["close_value"])

    except Exception as e:
        logger.error(f"load_historical_data_failed ticker={ticker} error={str(e)}")
        return None


# ── 스코어링 시뮬레이션 ───────────────────────────────────────────────────────

def _build_market_indicators_from_df(
    vix_df: Optional[pd.DataFrame],
    us10y_df: Optional[pd.DataFrame],
    krwusd_df: Optional[pd.DataFrame],
    t: pd.Timestamp,
) -> dict:
    """과거 시점의 시장 지표 딕셔너리 빌드"""
    indicators = {}
    try:
        if vix_df is not None and t in vix_df.index:
            indicators["VIX"] = {"value_value": float(vix_df.loc[t, "close_value"]), "stale": False}
    except Exception:
        pass
    try:
        if us10y_df is not None and t in us10y_df.index:
            val = float(us10y_df.loc[t].iloc[0])
            prev_idx = us10y_df.index.get_loc(t)
            prev_val = float(us10y_df.iloc[prev_idx - 1].iloc[0]) if prev_idx > 0 else val
            change_pct = round((val - prev_val) / prev_val * 100, 4) if prev_val else 0.0
            indicators["US10Y"] = {"change_pct": change_pct, "stale": False}
    except Exception:
        pass
    try:
        if krwusd_df is not None and t in krwusd_df.index:
            val = float(krwusd_df.loc[t, "close_value"])
            window = krwusd_df["close_value"].loc[:t].tail(20)
            bb_upper = round(float(window.mean() + 2 * window.std()), 4) if len(window) >= 20 else None
            indicators["KRWUSD"] = {
                "value_value": val, "bb_upper_value": bb_upper, "stale": False
            }
    except Exception:
        pass
    return indicators


def simulate_scoring(
    df: pd.DataFrame,
    market: str,
    vix_df: Optional[pd.DataFrame] = None,
    us10y_df: Optional[pd.DataFrame] = None,
    krwusd_df: Optional[pd.DataFrame] = None,
) -> list[AlertSignal]:
    """BR-01: shared/scoring.py 재사용. BR-03: Kill-Switch 적용."""
    signals = []
    dates = df.index[21:]  # RSI/MA 계산에 필요한 초기 데이터 제외

    for t in dates:
        try:
            row = df.loc[t]
            prev_idx = df.index.get_loc(t)
            prev_row = df.iloc[prev_idx - 1] if prev_idx > 0 else row

            # Kill-Switch (BR-03)
            indicators = _build_market_indicators_from_df(vix_df, us10y_df, krwusd_df, t)
            ks = evaluate_kill_switch(indicators)

            ctx = ScoringContext(
                ticker=str(df.attrs.get("ticker", "UNKNOWN")),
                market=market,
                date=t.strftime("%Y-%m-%d"),
                pbr_value=float(row["pbr_value"]) if pd.notna(row.get("pbr_value")) else None,
                pbr_min_value=float(row["pbr_min_rolling"]) if pd.notna(row.get("pbr_min_rolling")) else None,
                close_value=float(row["close_value"]) if pd.notna(row.get("close_value")) else None,
                ma20_value=float(row["ma20_value"]) if pd.notna(row.get("ma20_value")) else None,
                rsi_prev_level=float(prev_row["rsi_level"]) if pd.notna(prev_row.get("rsi_level")) else None,
                rsi_curr_level=float(row["rsi_level"]) if pd.notna(row.get("rsi_level")) else None,
                cumulative_net_buy_value=float(row["cum_net_buy_20d"]) if pd.notna(row.get("cum_net_buy_20d")) else None,
                prev_cumulative_net_buy_value=float(prev_row["cum_net_buy_20d"]) if pd.notna(prev_row.get("cum_net_buy_20d")) else None,
            )

            breakdown = calculate_total_score(ctx, market, ks)

            if breakdown.total_score >= ALERT_THRESHOLD:
                signals.append(AlertSignal(
                    ticker=ctx.ticker,
                    market=market,
                    signal_date=ctx.date,
                    entry_price_value=round(float(row["close_value"]), 4),
                    total_score=breakdown.total_score,
                    signals=breakdown.signals,
                ))
        except Exception as e:
            logger.warning(f"scoring_failed date={t} error={str(e)}")
            continue

    return signals


# ── 수익률 계산 ───────────────────────────────────────────────────────────────

def calculate_forward_returns(
    df: pd.DataFrame, signal_date: str, periods: list[int]
) -> dict[int, Optional[float]]:
    """BR-04: 알람 후 N거래일 수익률 계산 (change_pct)"""
    results = {}
    try:
        sig_ts = pd.Timestamp(signal_date)
        if sig_ts not in df.index:
            return {p: None for p in periods}
        entry_price_value = float(df.loc[sig_ts, "close_value"])
        trading_dates = df.index[df.index >= sig_ts]

        for period in periods:
            if len(trading_dates) > period:
                exit_price_value = float(df.iloc[df.index.get_loc(sig_ts) + period]["close_value"])
                change_pct = round((exit_price_value - entry_price_value) / entry_price_value * 100, 4)
                results[period] = change_pct
            else:
                results[period] = None
    except Exception as e:
        logger.warning(f"forward_return_failed signal_date={signal_date} error={str(e)}")
        results = {p: None for p in periods}
    return results


# ── 리포트 출력 ───────────────────────────────────────────────────────────────

def export_report(signals: list[AlertSignal], output_path: str) -> None:
    """BR-06: CSV 리포트 출력"""
    if not signals:
        logger.info("no_signals_found")
        print("\n[결과] 알람 발생 없음")
        return

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ticker", "market", "signal_date", "entry_price_value",
            "total_score", "return_60d_pct", "return_90d_pct", "return_150d_pct", "signals"
        ])
        writer.writeheader()
        for s in signals:
            writer.writerow({
                "ticker": s.ticker, "market": s.market,
                "signal_date": s.signal_date,
                "entry_price_value": s.entry_price_value,
                "total_score": s.total_score,
                "return_60d_pct": s.return_60d_pct,
                "return_90d_pct": s.return_90d_pct,
                "return_150d_pct": s.return_150d_pct,
                "signals": " | ".join(s.signals),
            })

    # 콘솔 요약
    valid_60 = [s.return_60d_pct for s in signals if s.return_60d_pct is not None]
    valid_90 = [s.return_90d_pct for s in signals if s.return_90d_pct is not None]
    print(f"\n[백테스팅 결과 요약]")
    print(f"  총 알람 수: {len(signals)}")
    print(f"  평균 수익률 (60거래일): {round(sum(valid_60)/len(valid_60), 2) if valid_60 else 'N/A'}%")
    print(f"  평균 수익률 (90거래일): {round(sum(valid_90)/len(valid_90), 2) if valid_90 else 'N/A'}%")
    print(f"  결과 파일: {output_path}")
    logger.info(f"report_exported path={output_path} signal_count={len(signals)}")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HCSES Backtesting Runner")
    parser.add_argument("--tickers", nargs="+", required=True)
    parser.add_argument("--market", choices=["KR", "US"], required=True)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--seed", action="store_true", help="StockStatsTable Seed 생성")
    parser.add_argument("--output", default=f"backtest_results_{datetime.now().strftime('%Y%m%d')}.csv")
    args = parser.parse_args()

    # 시장 지표 로드 (Kill-Switch용)
    logger.info("loading_market_indicators")
    vix_df = us10y_df = krwusd_df = None
    try:
        vix_raw = yf.download("^VIX", start=args.start, end=args.end, auto_adjust=True, progress=False)
        if not vix_raw.empty:
            if isinstance(vix_raw.columns, pd.MultiIndex):
                vix_raw.columns = vix_raw.columns.get_level_values(0)
            vix_df = vix_raw.rename(columns={"Close": "close_value"})
    except Exception as e:
        logger.warning(f"vix_load_failed error={str(e)}")

    try:
        import pandas_datareader.data as web
        us10y_df = web.DataReader("DGS10", "fred", args.start, args.end).dropna()
    except Exception as e:
        logger.warning(f"us10y_load_failed error={str(e)}")

    try:
        krw_raw = yf.download("KRW=X", start=args.start, end=args.end, auto_adjust=True, progress=False)
        if not krw_raw.empty:
            if isinstance(krw_raw.columns, pd.MultiIndex):
                krw_raw.columns = krw_raw.columns.get_level_values(0)
            krwusd_df = krw_raw.rename(columns={"Close": "close_value"})
    except Exception as e:
        logger.warning(f"krwusd_load_failed error={str(e)}")

    all_signals: list[AlertSignal] = []

    for ticker in args.tickers:
        logger.info(f"processing ticker={ticker}")
        df = load_historical_data(ticker, args.market, args.start, args.end)
        if df is None or df.empty:
            logger.warning(f"no_data ticker={ticker}")
            continue

        df.attrs["ticker"] = ticker
        signals = simulate_scoring(df, args.market, vix_df, us10y_df, krwusd_df)
        logger.info(f"signals_found ticker={ticker} count={len(signals)}")

        for sig in signals:
            returns = calculate_forward_returns(df, sig.signal_date, [60, 90, 150])
            sig.return_60d_pct = returns.get(60)
            sig.return_90d_pct = returns.get(90)
            sig.return_150d_pct = returns.get(150)

        all_signals.extend(signals)
        time.sleep(random.uniform(1, 3))  # Rate Limiting

    # Seed Data 생성 (--seed 옵션)
    if args.seed:
        from src.backtesting.seed_migrator import generate_and_migrate_seed
        generate_and_migrate_seed(args.tickers, args.start, args.end)

    export_report(all_signals, args.output)


if __name__ == "__main__":
    main()
