# Unit 1: DataCollector - Tech Stack Decisions

| 항목 | 선택 | 근거 |
|---|---|---|
| 런타임 | Python 3.12 | 요구사항 명시 |
| 데이터 수집 | yfinance 0.2.x | OHLCV, PBR, PER, RSI, 환율 |
| 한국 수급 | FinanceDataReader | KRX 투자자별 매매 데이터 |
| 매크로 지표 | pandas_datareader + FRED | VIX, US10Y |
| 수치 처리 | pandas, numpy | DataFrame 기반 계산 |
| AWS SDK | boto3 | DynamoDB, Secrets Manager |
| 로깅 | Python logging + JSON formatter | 구조화 로그 |
| 시간대 처리 | pytz | DST 감지 (Unit 2와 공유) |
| 배포 | AWS SAM | Lambda + EventBridge |
