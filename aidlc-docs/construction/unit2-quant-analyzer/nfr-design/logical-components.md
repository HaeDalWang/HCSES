# Unit 2: QuantAnalyzer - Logical Components

## Lambda: QuantAnalyzerKR / QuantAnalyzerUS
- 메모리: 256MB
- 타임아웃: 300초
- 환경변수: MARKET, STOCK_DAILY_TABLE, STOCK_STATS_TABLE, MARKET_INDICATOR_TABLE, ALERTING_ENGINE_ARN

## EventBridge Rules (KR — 장 중 10회 분산)
```
cron(0 0 ? * MON-FRI *)   # 09:00 KST
cron(30 0 ? * MON-FRI *)  # 09:30 KST
cron(0 1 ? * MON-FRI *)   # 10:00 KST
cron(0 2 ? * MON-FRI *)   # 11:00 KST
cron(0 3 ? * MON-FRI *)   # 12:00 KST
cron(0 4 ? * MON-FRI *)   # 13:00 KST
cron(0 5 ? * MON-FRI *)   # 14:00 KST
cron(30 5 ? * MON-FRI *)  # 14:30 KST
cron(0 6 ? * MON-FRI *)   # 15:00 KST
cron(20 6 ? * MON-FRI *)  # 15:20 KST
```

## EventBridge Rules (US — EDT 기준, 장 중 10회)
```
cron(30 13 ? * MON-FRI *) # 09:30 EDT (장 시작)
cron(0 14 ? * MON-FRI *)
cron(0 15 ? * MON-FRI *)
cron(0 16 ? * MON-FRI *)
cron(0 17 ? * MON-FRI *)
cron(0 18 ? * MON-FRI *)
cron(0 19 ? * MON-FRI *)
cron(30 19 ? * MON-FRI *)
cron(0 20 ? * MON-FRI *)  # 16:00 EDT (장 마감)
cron(55 19 ? * MON-FRI *) # 15:55 EDT (마감 직전)
```
# EST 시즌에는 Lambda 내부 DST 감지로 1시간 보정

## IAM: Lambda Execution Role
- DynamoDB: GetItem, Query (StockDailyTable, StockStatsTable, MarketIndicatorTable)
- DynamoDB: UpdateItem (StockDailyTable — analysis_status 업데이트)
- Lambda: InvokeFunction (AlertingEngine ARN 한정)
- CloudWatch Logs: 기본 권한
