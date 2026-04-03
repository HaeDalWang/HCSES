"""
DataCollector 수집 서비스
FR-02, EC-01, EC-02, BR-01~09
"""
import logging
import time
import random
from datetime import datetime, date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from src.shared.models import StockDailyRecord, MarketIndicatorRecord

logger = logging.getLogger(__name__)


# ── 수치 정규화 ──────────────────────────────────────────────────────────────

def normalize_numeric_fields(record: StockDailyRecord) -> StockDailyRecord:
    """BR-02: 모든 float 필드 소수점 4자리 반올림. None은 유지."""
    float_fields = [
        "open_value", "high_value", "low_value", "close_value",
        "pbr_value", "per_value", "rsi_level", "ma20_value",
        "foreign_net_buy_value", "institution_net_buy_value",
    ]
    for f in float_fields:
        v = getattr(record, f)
        if v is not None:
            setattr(record, f, round(float(v), 4))
    return record


# ── RSI / MA 계산 ─────────────────────────────────────────────────────────────

def _calc_rsi(closes: pd.Series, period: int = 14) -> Optional[float]:
    """
    RSI(14) 계산 — Wilder's Smoothing (ewm, alpha=1/period).
    SMA rolling().mean() 대신 표준 지수 평활화 사용.
    데이터 부족 시 None 반환.
    """
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, min_periods=period).mean()
    last_loss = loss.iloc[-1]
    if last_loss == 0 or pd.isna(last_loss):
        return 100.0
    rs = gain.iloc[-1] / last_loss
    return round(100 - (100 / (1 + rs)), 4)


def _calc_ma20(closes: pd.Series) -> Optional[float]:
    if len(closes) < 20:
        return None
    return round(float(closes.tail(20).mean()), 4)


# ── 종목 데이터 수집 ──────────────────────────────────────────────────────────

def _fetch_pbr_from_fdr(ticker: str) -> Optional[float]:
    """
    EC-01: KR 종목 PBR fallback
    yfinance quarterly_balance_sheet에서 BPS 직접 계산 후 현재가로 PBR 산출.
    FDR StockListing("KRX")는 API 불안정으로 사용하지 않음.
    """
    try:
        tk = yf.Ticker(ticker)
        bs = tk.quarterly_balance_sheet
        if bs is None or bs.empty:
            return None
        if "Stockholders Equity" not in bs.index or "Ordinary Shares Number" not in bs.index:
            return None

        equity = bs.loc["Stockholders Equity"].iloc[0]
        shares = bs.loc["Ordinary Shares Number"].iloc[0]
        if not equity or not shares or float(shares) <= 0:
            return None

        bps = float(equity) / float(shares)
        if bps <= 0:
            return None

        price = tk.info.get("currentPrice") or tk.info.get("regularMarketPrice")
        if not price or float(price) <= 0:
            return None

        pbr = round(float(price) / bps, 4)
        logger.info(f"pbr_from_balance_sheet ticker={ticker} bps={bps:.0f} pbr={pbr}")
        return pbr
    except Exception as e:
        logger.warning(f"balance_sheet_pbr_failed ticker={ticker} error={str(e)}")
        return None


def collect_stock_data(
    ticker: str, market: str, target_date: date
) -> Optional[StockDailyRecord]:
    """
    BR-01: Adjusted Close 강제 사용 (auto_adjust=True)
    BR-03: PBR 결측 시 FDR fallback
    BR-05: 빈 DataFrame → None 반환 (휴장일 처리)
    """
    try:
        # 최근 25거래일 데이터 (RSI 14 + MA 20 계산용)
        end = target_date + timedelta(days=1)
        start = target_date - timedelta(days=40)
        df = yf.download(
            ticker, start=start.isoformat(), end=end.isoformat(),
            auto_adjust=True, progress=False, threads=False
        )
        if df.empty:
            logger.info(f"empty_data_skip ticker={ticker} date={target_date}")
            return None

        # 컬럼 평탄화 (MultiIndex 방지)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        latest = df.iloc[-1]
        closes = df["Close"]

        # PBR / PER
        pbr_value: Optional[float] = None
        per_value: Optional[float] = None
        try:
            info = yf.Ticker(ticker).info
            raw_pbr = info.get("priceToBook")
            raw_per = info.get("trailingPE")
            if raw_pbr is not None and not np.isnan(float(raw_pbr)):
                pbr_value = round(float(raw_pbr), 4)
            if raw_per is not None and not np.isnan(float(raw_per)):
                per_value = round(float(raw_per), 4)
        except Exception:
            pass

        # EC-01: KR PBR 결측 시 FDR fallback
        if pbr_value is None and market == "KR":
            pbr_value = _fetch_pbr_from_fdr(ticker)
            if pbr_value is None:
                logger.warning(f"pbr_missing ticker={ticker} date={target_date} market={market}")

        record = StockDailyRecord(
            ticker=ticker,
            market=market,
            date=target_date.isoformat(),
            open_value=round(float(latest["Open"]), 4),
            high_value=round(float(latest["High"]), 4),
            low_value=round(float(latest["Low"]), 4),
            close_value=round(float(latest["Close"]), 4),
            volume_value=int(latest["Volume"]),
            pbr_value=pbr_value,
            per_value=per_value,
            rsi_level=_calc_rsi(closes),
            ma20_value=_calc_ma20(closes),
            data_status="COLLECTING",
            analysis_status="PENDING",
            collected_at=datetime.utcnow().isoformat(),
        )
        return normalize_numeric_fields(record)

    except Exception as e:
        logger.error(f"collect_stock_data_failed ticker={ticker} error={str(e)}")
        return None


# ── 한국 수급 데이터 ──────────────────────────────────────────────────────────

def collect_kr_supply_demand(
    ticker: str, target_date: date
) -> tuple[Optional[float], Optional[float]]:
    """
    BR-08: 외국인/기관 순매수 수집 (KR only)
    반환: (foreign_net_buy_value, institution_net_buy_value)
    """
    try:
        import FinanceDataReader as fdr
        code = ticker.replace(".KS", "").replace(".KQ", "")
        end = target_date + timedelta(days=1)
        start = target_date - timedelta(days=1)
        df = fdr.DataReader(code, start.isoformat(), end.isoformat())
        if df.empty:
            return None, None
        latest = df.iloc[-1]
        foreign = latest.get("ForeignNetBuy") or latest.get("외국인순매수")
        institution = latest.get("InstitutionNetBuy") or latest.get("기관순매수")
        f_val = round(float(foreign), 4) if foreign is not None and not np.isnan(float(foreign)) else None
        i_val = round(float(institution), 4) if institution is not None and not np.isnan(float(institution)) else None
        return f_val, i_val
    except Exception as e:
        logger.warning(f"supply_demand_failed ticker={ticker} error={str(e)}")
        return None, None


# ── 시장 지표 수집 ────────────────────────────────────────────────────────────

def _calc_bollinger_bands(series: pd.Series, window: int = 20) -> tuple[Optional[float], Optional[float]]:
    if len(series) < window:
        return None, None
    tail = series.tail(window)
    ma = tail.mean()
    std = tail.std()
    return round(float(ma + 2 * std), 4), round(float(ma - 2 * std), 4)


def collect_market_indicators(target_date: date) -> list[MarketIndicatorRecord]:
    """BR-09: VIX, US10Y, KRW/USD 수집"""
    records = []
    end = target_date + timedelta(days=1)
    start = target_date - timedelta(days=30)

    # VIX
    try:
        df = yf.download("^VIX", start=start.isoformat(), end=end.isoformat(),
                         auto_adjust=True, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            today_val = round(float(df["Close"].iloc[-1]), 4)
            prev_val = round(float(df["Close"].iloc[-2]), 4) if len(df) >= 2 else None
            change_pct = round((today_val - prev_val) / prev_val * 100, 4) if prev_val else None
            records.append(MarketIndicatorRecord(
                indicator="VIX", date=target_date.isoformat(),
                value_value=today_val, prev_value=prev_val, change_pct=change_pct,
                collected_at=datetime.utcnow().isoformat()
            ))
    except Exception as e:
        logger.error(f"vix_collection_failed error={str(e)}")

    # US10Y (yfinance ^TNX — FRED 대체, 타임아웃 이슈 해결)
    try:
        df = yf.download("^TNX", start=start.isoformat(), end=end.isoformat(),
                         auto_adjust=True, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            today_val = round(float(df["Close"].iloc[-1]), 4)
            prev_val = round(float(df["Close"].iloc[-2]), 4) if len(df) >= 2 else None
            change_pct = round((today_val - prev_val) / prev_val * 100, 4) if prev_val else None
            records.append(MarketIndicatorRecord(
                indicator="US10Y", date=target_date.isoformat(),
                value_value=today_val, prev_value=prev_val, change_pct=change_pct,
                collected_at=datetime.utcnow().isoformat()
            ))
    except Exception as e:
        logger.error(f"us10y_collection_failed error={str(e)}")

    # KRW/USD + 볼린저 밴드
    try:
        df = yf.download("KRW=X", start=start.isoformat(), end=end.isoformat(),
                         auto_adjust=True, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            closes = df["Close"]
            today_val = round(float(closes.iloc[-1]), 4)
            prev_val = round(float(closes.iloc[-2]), 4) if len(closes) >= 2 else None
            change_pct = round((today_val - prev_val) / prev_val * 100, 4) if prev_val else None
            bb_upper, bb_lower = _calc_bollinger_bands(closes)
            records.append(MarketIndicatorRecord(
                indicator="KRWUSD", date=target_date.isoformat(),
                value_value=today_val, prev_value=prev_val, change_pct=change_pct,
                bb_upper_value=bb_upper, bb_lower_value=bb_lower,
                collected_at=datetime.utcnow().isoformat()
            ))
    except Exception as e:
        logger.error(f"krwusd_collection_failed error={str(e)}")

    return records
