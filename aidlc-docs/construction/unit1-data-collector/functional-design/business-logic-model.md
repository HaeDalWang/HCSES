# Unit 1: DataCollector - Business Logic Model

## 전체 실행 흐름

```
handler(event, context)
  │
  ├─ market = event.get('market', 'KR')  # EventBridge에서 주입
  ├─ today = get_trading_date(market)
  │
  ├─ [BR-05] is_market_holiday(market, today) → True: 조기 종료 (정상)
  │
  ├─ tickers = load_ticker_list(market)
  │
  ├─ for ticker in tickers:
  │   ├─ record = collect_stock_data(ticker, market, today)
  │   │   ├─ yfinance download(ticker, period='1d', auto_adjust=True)
  │   │   ├─ 빈 DataFrame → None 반환 (휴장일 처리)
  │   │   ├─ RSI(14) 계산: 최근 15일 데이터 필요
  │   │   ├─ MA20 계산: 최근 20일 데이터 필요
  │   │   ├─ [BR-03] PBR 결측 시 FDR fallback
  │   │   └─ [BR-02] normalize_numeric_fields()
  │   │
  │   ├─ record is None → skip (log WARNING)
  │   │
  │   ├─ [KR only] supply = collect_kr_supply_demand(ticker, today)
  │   │   └─ record에 병합
  │   │
  │   ├─ [BR-06] save_stock_daily(record)  ← data_status: COLLECTING→COMPLETE
  │   │   └─ [BR-07] 멱등성 체크
  │   │
  │   └─ [BR-04] sleep(random.uniform(1, 3))
  │
  └─ indicators = collect_market_indicators(today)
      ├─ VIX, US10Y, KRW/USD 수집
      ├─ 볼린저 밴드 계산 (KRW/USD)
      ├─ change_pct 계산
      └─ save_market_indicator(indicators)
```

## RSI(14) 계산 로직

```
1. 최근 15거래일 Adjusted Close 수집
2. daily_change = close[i] - close[i-1]
3. gains = [max(c, 0) for c in daily_change]
4. losses = [abs(min(c, 0)) for c in daily_change]
5. avg_gain = mean(gains[-14:])
6. avg_loss = mean(losses[-14:])
7. rs = avg_gain / avg_loss  (avg_loss == 0 → rsi_level = 100.0)
8. rsi_level = round(100 - (100 / (1 + rs)), 4)
```

## 볼린저 밴드 계산 로직 (KRW/USD)

```
1. 최근 20거래일 KRW/USD close_value 수집
2. ma20_value = mean(close[-20:])
3. std_value = std(close[-20:])
4. bb_upper_value = round(ma20_value + 2 * std_value, 4)
5. bb_lower_value = round(ma20_value - 2 * std_value, 4)
```

## TTL 계산

```
ttl = int((datetime.utcnow() + timedelta(days=180)).timestamp())
```
