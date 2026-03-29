# Unit 2: QuantAnalyzer - Domain Entities

## KillSwitchResult
```
active: bool                   # Kill-Switch 활성화 여부
reason: str                    # 활성화 이유 (빈 문자열이면 비활성)
vix_value: float | None
yield_change_pct: float | None
krwusd_value: float | None
krwusd_bb_upper_value: float | None
```

## ScoringContext
```
ticker: str
market: str                    # "KR" | "US"
date: str
# Valuation
pbr_value: float | None
pbr_min_value: float | None    # StockStatsTable에서 조회
# Momentum
close_value: float | None
ma20_value: float | None
rsi_prev_level: float | None   # 전일 RSI
rsi_curr_level: float | None   # 당일 RSI
# Supply/Demand (KR only)
foreign_net_buy_value: float | None
institution_net_buy_value: float | None
cumulative_net_buy_value: float | None  # 20거래일 누적합
prev_cumulative_net_buy_value: float | None  # 전일 누적합 (양전 감지용)
```

## ScoreBreakdown
```
valuation_score: float         # 0 또는 만점 (KR:40, US:60)
momentum_score: float          # 0 또는 만점 (KR:30, US:40)
supply_demand_score: float     # 0 또는 30 (KR only)
total_score: float             # 합산 (Kill-Switch 시 0.0 강제)
signals: list[str]             # 감지된 시그널 설명 목록
```
