# Unit 1: DataCollector - Domain Entities

## StockDailyRecord
```
ticker: str                    # 종목 코드 (예: "005930.KS", "AAPL")
market: str                    # "KR" | "US"
date: str                      # "YYYY-MM-DD"
open_value: float              # 시가 (Adjusted)
high_value: float              # 고가 (Adjusted)
low_value: float               # 저가 (Adjusted)
close_value: float             # 종가 (Adjusted Close)
volume_value: int              # 거래량
pbr_value: float | None        # PBR (결측 가능)
per_value: float | None        # PER (결측 가능)
rsi_level: float | None        # RSI(14)
ma20_value: float | None       # 20일 이동평균
foreign_net_buy_value: float | None   # 외국인 순매수 (KR only)
institution_net_buy_value: float | None  # 기관 순매수 (KR only)
data_status: str               # "COLLECTING" | "COMPLETE" | "FAILED"
analysis_status: str           # "PENDING" | "DONE"
collected_at: str              # ISO 8601 timestamp
ttl: int                       # Unix timestamp (180일 후)
```

## MarketIndicatorRecord
```
indicator: str                 # "VIX" | "US10Y" | "KRWUSD"
date: str                      # "YYYY-MM-DD"
value_value: float             # 지표 수치
prev_value: float | None       # 전일 수치 (변동률 계산용)
change_pct: float | None       # 전일 대비 변동률 (%)
bb_upper_value: float | None   # 볼린저 밴드 상단 (KRWUSD only)
bb_lower_value: float | None   # 볼린저 밴드 하단 (KRWUSD only)
collected_at: str
ttl: int                       # Unix timestamp (180일 후)
```

## TickerConfig
```
ticker: str
market: str                    # "KR" | "US"
name: str                      # 종목명
enabled: bool
```
