# Unit 4: Backtesting - Business Logic Model

## 실행 흐름

```
CLI: python -m src.backtesting.backtest_runner \
     --tickers 005930.KS AAPL \
     --market KR \
     --start 2021-01-01 \
     --end 2023-12-31 \
     --seed  # StockStatsTable Seed 생성 포함

backtest_runner.main()
  │
  ├─ load_historical_data(ticker, start, end, market)
  │   ├─ yfinance download (auto_adjust=True)
  │   └─ KR PBR 결측 시 FDR 로컬 캐시 fallback
  │
  ├─ simulate_scoring(df, market)
  │   ├─ 날짜별 ScoringContext 빌드
  │   ├─ shared/scoring.py 스코어링 함수 호출 (BR-01)
  │   └─ score >= 90 → AlertSignal 기록
  │
  ├─ for each signal:
  │   └─ calculate_forward_returns(df, signal_date, [60, 90, 150])
  │
  ├─ [--seed 옵션] generate_seed_data(tickers) → migrate_seed_data()
  │
  └─ export_report(results, output_path)
```

## 히스토리컬 ScoringContext 빌드

```python
# 날짜 t에서의 컨텍스트
ctx = ScoringContext(
    ticker=ticker, market=market, date=t,
    pbr_value=df.loc[t, "pbr_value"],
    pbr_min_value=stats["pbr_min_value"],   # 해당 시점까지의 rolling min
    close_value=df.loc[t, "close_value"],
    ma20_value=df.loc[t, "ma20_value"],
    rsi_prev_level=df.loc[t-1, "rsi_level"],
    rsi_curr_level=df.loc[t, "rsi_level"],
    # KR: 20거래일 누적 순매수합 (rolling sum)
    cumulative_net_buy_value=df.loc[t, "cum_net_buy_20d"],
    prev_cumulative_net_buy_value=df.loc[t-1, "cum_net_buy_20d"],
)
```

## Rolling PBR Min (백테스팅 전용)

실운영과 달리 백테스팅에서는 미래 데이터 누출(look-ahead bias) 방지를 위해
해당 날짜까지의 rolling minimum PBR을 사용:
```python
df["pbr_min_rolling"] = df["pbr_value"].expanding().min()
```
