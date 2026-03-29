# Unit 2: QuantAnalyzer - Business Logic Model

## 전체 실행 흐름

```
handler(event, context)
  │
  ├─ market = event.get('market')
  ├─ now = datetime.utcnow()
  │
  ├─ [BR-08] is_within_market_hours(market, now) → False: 조기 종료
  │
  ├─ indicators = load_market_indicators(today)
  ├─ [BR-02] kill_switch = evaluate_kill_switch(indicators)
  │   └─ active=True: 로그 후 조기 종료 (score=0 처리 불필요, 분석 자체 skip)
  │
  ├─ tickers = load_ticker_list(market)
  │
  ├─ for ticker in tickers:
  │   ├─ [BR-06] record = get_latest_complete_record(ticker, today)
  │   │   └─ None → skip (이미 DONE 또는 데이터 없음)
  │   │
  │   ├─ stats = get_stock_stats(ticker)  ← StockStatsTable
  │   │
  │   ├─ ctx = build_scoring_context(record, stats, market)
  │   │
  │   ├─ breakdown = calculate_score(ctx, market)
  │   │   ├─ [BR-03] valuation_score
  │   │   ├─ [BR-04] momentum_score
  │   │   ├─ [BR-05] supply_demand_score (KR only)
  │   │   └─ total = sum (Kill-Switch 비활성 확인 후)
  │   │
  │   ├─ [BR-06] mark_analysis_done(ticker, today)
  │   │
  │   └─ [BR-07] total_score >= 90 → invoke AlertingEngine(ticker, breakdown)
  │
  └─ 완료 로그
```

## Kill-Switch 평가 로직

```python
def evaluate_kill_switch(indicators: dict) -> KillSwitchResult:
    # VIX
    vix = indicators.get("VIX", {}).get("value_value")
    if vix is not None and vix > 30:
        return KillSwitchResult(active=True, reason=f"VIX={vix}>30")

    # US10Y 변동률
    yield_chg = indicators.get("US10Y", {}).get("change_pct")
    if yield_chg is not None and yield_chg > 3.0:
        return KillSwitchResult(active=True, reason=f"US10Y_change_pct={yield_chg}>3%")

    # KRW/USD 볼린저 상단 돌파
    krw = indicators.get("KRWUSD", {})
    val = krw.get("value_value")
    upper = krw.get("bb_upper_value")
    if val is not None and upper is not None and val > upper:
        return KillSwitchResult(active=True, reason=f"KRWUSD={val}>BB_upper={upper}")

    return KillSwitchResult(active=False, reason="")
```

## 스코어링 로직 (shared/scoring.py로 분리)

```python
# KR 가중치
KR_WEIGHTS = {"valuation": 40, "momentum": 30, "supply_demand": 30}
# US 가중치
US_WEIGHTS = {"valuation": 60, "momentum": 40, "supply_demand": 0}

def calculate_valuation_floor_score(ctx, market) -> float:
    if ctx.pbr_value is None or ctx.pbr_min_value is None:
        return 0.0  # BR-01
    threshold = round(ctx.pbr_min_value * 1.1, 4)
    if ctx.pbr_value <= threshold:
        weights = KR_WEIGHTS if market == "KR" else US_WEIGHTS
        return float(weights["valuation"])
    return 0.0

def calculate_momentum_pivot_score(ctx, market) -> float:
    if any(v is None for v in [ctx.close_value, ctx.ma20_value,
                                ctx.rsi_prev_level, ctx.rsi_curr_level]):
        return 0.0  # BR-01
    if (ctx.close_value > ctx.ma20_value and
            ctx.rsi_prev_level <= 30 and ctx.rsi_curr_level > 35):
        weights = KR_WEIGHTS if market == "KR" else US_WEIGHTS
        return float(weights["momentum"])
    return 0.0

def calculate_supply_demand_score(ctx, market) -> float:
    if market != "KR":
        return 0.0
    if ctx.cumulative_net_buy_value is None or ctx.prev_cumulative_net_buy_value is None:
        return 0.0  # BR-01
    # 양전 전환 감지
    if (ctx.cumulative_net_buy_value > 0 and
            ctx.prev_cumulative_net_buy_value <= 0):
        return 30.0
    return 0.0
```
