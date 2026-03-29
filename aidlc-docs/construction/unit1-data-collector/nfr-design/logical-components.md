# Unit 1: DataCollector - Logical Components

## Lambda Function: DataCollector
- 메모리: 512MB
- 타임아웃: 900초 (15분)
- 런타임: python3.12
- 환경변수: MARKET (KR|US), TABLE_NAME_DAILY, TABLE_NAME_INDICATOR

## Lambda Function: StatsUpdater
- 메모리: 256MB
- 타임아웃: 300초 (5분)
- 런타임: python3.12

## DynamoDB: StockDailyTable
- 파티션 키: ticker (S)
- 정렬 키: date (S)
- TTL 속성: ttl
- GSI: StatusDateIndex (data_status, date) — QuantAnalyzer 조회용

## DynamoDB: MarketIndicatorTable
- 파티션 키: indicator (S)
- 정렬 키: date (S)
- TTL 속성: ttl

## DynamoDB: StockStatsTable
- 파티션 키: ticker (S)
- 정렬 키: stat_type (S)
- TTL: 없음 (영구)

## EventBridge Rules
- KR_Collector: `cron(30 7 ? * MON-FRI *)` (UTC = KST 16:30)
- US_Collector_EDT: `cron(30 21 ? * MON-FRI *)` (UTC = EDT 장 마감 후)
- US_Collector_EST: `cron(30 22 ? * MON-FRI *)` (UTC = EST 장 마감 후)
- StatsUpdater: `cron(0 0 ? * SAT *)`

## IAM: Lambda Execution Role
- DynamoDB: PutItem, UpdateItem, GetItem (StockDailyTable, MarketIndicatorTable, StockStatsTable)
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
- Secrets Manager: GetSecretValue (특정 ARN만)
- 와일드카드 리소스 금지 (SECURITY-06)
