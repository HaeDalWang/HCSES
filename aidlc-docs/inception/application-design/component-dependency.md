# HCSES - Component Dependencies

## 의존성 매트릭스

| 컴포넌트 | 의존 대상 | 의존 유형 |
|---|---|---|
| DataCollector | yfinance | 외부 라이브러리 (OHLCV, PBR, PER, RSI, 환율) |
| DataCollector | FinanceDataReader | 외부 라이브러리 (KR 수급 데이터) |
| DataCollector | pandas_datareader | 외부 라이브러리 (VIX, US10Y) |
| DataCollector | DynamoDB StockDailyTable | AWS 서비스 (쓰기) |
| DataCollector | DynamoDB MarketIndicatorTable | AWS 서비스 (쓰기) |
| DataCollector | Secrets Manager | AWS 서비스 (읽기 - AWS 자격증명) |
| QuantAnalyzer | DynamoDB StockDailyTable | AWS 서비스 (읽기, data_status=COMPLETE) |
| QuantAnalyzer | DynamoDB StockStatsTable | AWS 서비스 (읽기) |
| QuantAnalyzer | DynamoDB MarketIndicatorTable | AWS 서비스 (읽기) |
| QuantAnalyzer | AlertingEngine | Lambda Invoke (동기 호출) |
| AlertingEngine | Secrets Manager | AWS 서비스 (읽기 - Discord Webhook URL, 캐싱) |
| AlertingEngine | Discord Webhook | 외부 HTTP API |
| AlertingEngine | DynamoDB StockStatsTable | AWS 서비스 (읽기 - 목표가/손절가 계산) |
| Backtesting | yfinance | 외부 라이브러리 |
| Backtesting | FinanceDataReader | 외부 라이브러리 |
| Backtesting | DynamoDB StockStatsTable | AWS 서비스 (쓰기 - Seed Data) |
| Backtesting | QuantAnalyzer (로직) | 코드 공유 (scoring 모듈 재사용) |
| StatsUpdater | yfinance | 외부 라이브러리 |
| StatsUpdater | DynamoDB StockStatsTable | AWS 서비스 (읽기/쓰기) |

---

## 데이터 흐름도

```
EventBridge (Daily KR/US)
        |
        v
  DataCollector
  [yfinance / FDR / pandas_datareader]
        |
        v
  StockDailyTable (data_status: COMPLETE)
  MarketIndicatorTable
        |
        v
EventBridge (KR_Market_Hours / US_Market_Hours)
        |
        v
  QuantAnalyzer
  [StockStatsTable 참조]
        |
        | score >= 90
        v
  AlertingEngine
  [Secrets Manager → Discord Webhook]

EventBridge (매주 토요일)
        |
        v
  StatsUpdater
  [yfinance → StockStatsTable]

CLI (수동)
        |
        v
  Backtesting
  [yfinance → 리포트 + StockStatsTable Seed]
```

---

## 공유 모듈 (Shared)

| 모듈명 | 사용 컴포넌트 | 내용 |
|---|---|---|
| `scoring.py` | QuantAnalyzer, Backtesting | 스코어링 로직 (Valuation, Momentum, Supply/Demand) |
| `market_calendar.py` | DataCollector, QuantAnalyzer | 공휴일/휴장일, DST 감지 |
| `dynamodb_client.py` | 전체 | DynamoDB 공통 클라이언트 (멱등성 헬퍼 포함) |
| `secrets_cache.py` | AlertingEngine, DataCollector | Secrets Manager 전역 캐싱 |
| `models.py` | 전체 | 데이터 모델 (StockDailyRecord, AnalysisResult 등) |
