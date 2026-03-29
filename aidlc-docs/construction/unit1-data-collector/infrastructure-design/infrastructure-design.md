# Unit 1: DataCollector - Infrastructure Design

## AWS SAM 리소스 매핑

### Lambda Functions

```yaml
DataCollectorKR:
  Type: AWS::Serverless::Function
  Properties:
    Handler: src/data_collector/handler.handler
    Runtime: python3.12
    MemorySize: 512
    Timeout: 900
    Environment:
      Variables:
        MARKET: KR
        STOCK_DAILY_TABLE: !Ref StockDailyTable
        MARKET_INDICATOR_TABLE: !Ref MarketIndicatorTable
    Events:
      KRSchedule:
        Type: Schedule
        Properties:
          Schedule: cron(30 7 ? * MON-FRI *)
          Input: '{"market": "KR"}'
    Policies:
      - DynamoDBCrudPolicy:
          TableName: !Ref StockDailyTable
      - DynamoDBCrudPolicy:
          TableName: !Ref MarketIndicatorTable
      - DynamoDBCrudPolicy:
          TableName: !Ref StockStatsTable

DataCollectorUS:
  Type: AWS::Serverless::Function
  Properties:
    Handler: src/data_collector/handler.handler
    Runtime: python3.12
    MemorySize: 512
    Timeout: 900
    Environment:
      Variables:
        MARKET: US
    Events:
      USScheduleEDT:
        Type: Schedule
        Properties:
          Schedule: cron(30 21 ? * MON-FRI *)
          Input: '{"market": "US"}'

StatsUpdaterFunction:
  Type: AWS::Serverless::Function
  Properties:
    Handler: src/stats_updater/handler.handler
    Runtime: python3.12
    MemorySize: 256
    Timeout: 300
    Events:
      WeeklySchedule:
        Type: Schedule
        Properties:
          Schedule: cron(0 0 ? * SAT *)
```

### DynamoDB Tables

```yaml
StockDailyTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: hcses-stock-daily
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: ticker
        AttributeType: S
      - AttributeName: date
        AttributeType: S
      - AttributeName: data_status
        AttributeType: S
    KeySchema:
      - AttributeName: ticker
        KeyType: HASH
      - AttributeName: date
        KeyType: RANGE
    GlobalSecondaryIndexes:
      - IndexName: StatusDateIndex
        KeySchema:
          - AttributeName: data_status
            KeyType: HASH
          - AttributeName: date
            KeyType: RANGE
        Projection:
          ProjectionType: ALL
    TimeToLiveSpecification:
      AttributeName: ttl
      Enabled: true
    SSESpecification:
      SSEEnabled: true   # SECURITY-01: 저장 시 암호화

StockStatsTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: hcses-stock-stats
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: ticker
        AttributeType: S
      - AttributeName: stat_type
        AttributeType: S
    KeySchema:
      - AttributeName: ticker
        KeyType: HASH
      - AttributeName: stat_type
        KeyType: RANGE
    SSESpecification:
      SSEEnabled: true   # SECURITY-01

MarketIndicatorTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: hcses-market-indicator
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: indicator
        AttributeType: S
      - AttributeName: date
        AttributeType: S
    KeySchema:
      - AttributeName: indicator
        KeyType: HASH
      - AttributeName: date
        KeyType: RANGE
    TimeToLiveSpecification:
      AttributeName: ttl
      Enabled: true
    SSESpecification:
      SSEEnabled: true   # SECURITY-01
```

### Secrets Manager
```yaml
# 수동 생성 (SAM 외부)
# Secret Name: hcses/discord-webhook-url
# Secret Name: hcses/api-keys (필요 시)
# Lambda Role에 GetSecretValue 권한 부여 (특정 ARN만)
```

### CloudWatch Log Groups
```yaml
# Lambda 자동 생성 + 보존 기간 설정
LogRetentionDays: 90   # SECURITY-14: 최소 90일
```
