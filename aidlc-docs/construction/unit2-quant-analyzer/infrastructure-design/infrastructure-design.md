# Unit 2: QuantAnalyzer - Infrastructure Design

## SAM 추가 리소스 (template.yaml에 병합)

```yaml
QuantAnalyzerKR:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: hcses-quant-analyzer-kr
    Handler: src/quant_analyzer/handler.handler
    MemorySize: 256
    Timeout: 300
    Environment:
      Variables:
        MARKET: KR
        ALERTING_ENGINE_ARN: !GetAtt AlertingEngineFunction.Arn
    Events:
      KROpen:    { Type: Schedule, Properties: { Schedule: "cron(0 0 ? * MON-FRI *)",  Input: '{"market":"KR"}' } }
      KRMid1:   { Type: Schedule, Properties: { Schedule: "cron(30 0 ? * MON-FRI *)", Input: '{"market":"KR"}' } }
      KRMid2:   { Type: Schedule, Properties: { Schedule: "cron(0 1 ? * MON-FRI *)",  Input: '{"market":"KR"}' } }
      KRMid3:   { Type: Schedule, Properties: { Schedule: "cron(0 2 ? * MON-FRI *)",  Input: '{"market":"KR"}' } }
      KRMid4:   { Type: Schedule, Properties: { Schedule: "cron(0 3 ? * MON-FRI *)",  Input: '{"market":"KR"}' } }
      KRMid5:   { Type: Schedule, Properties: { Schedule: "cron(0 4 ? * MON-FRI *)",  Input: '{"market":"KR"}' } }
      KRMid6:   { Type: Schedule, Properties: { Schedule: "cron(0 5 ? * MON-FRI *)",  Input: '{"market":"KR"}' } }
      KRMid7:   { Type: Schedule, Properties: { Schedule: "cron(30 5 ? * MON-FRI *)", Input: '{"market":"KR"}' } }
      KRMid8:   { Type: Schedule, Properties: { Schedule: "cron(0 6 ? * MON-FRI *)",  Input: '{"market":"KR"}' } }
      KRClose:  { Type: Schedule, Properties: { Schedule: "cron(20 6 ? * MON-FRI *)", Input: '{"market":"KR"}' } }
    Policies:
      - DynamoDBReadPolicy:
          TableName: !Ref StockDailyTable
      - DynamoDBReadPolicy:
          TableName: !Ref StockStatsTable
      - DynamoDBReadPolicy:
          TableName: !Ref MarketIndicatorTable
      - Statement:
          - Effect: Allow
            Action: dynamodb:UpdateItem
            Resource: !GetAtt StockDailyTable.Arn
      - Statement:
          - Effect: Allow
            Action: lambda:InvokeFunction
            Resource: !GetAtt AlertingEngineFunction.Arn

QuantAnalyzerUS:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: hcses-quant-analyzer-us
    Handler: src/quant_analyzer/handler.handler
    MemorySize: 256
    Timeout: 300
    Environment:
      Variables:
        MARKET: US
        ALERTING_ENGINE_ARN: !GetAtt AlertingEngineFunction.Arn
    Events:
      USOpen:   { Type: Schedule, Properties: { Schedule: "cron(30 13 ? * MON-FRI *)", Input: '{"market":"US"}' } }
      USMid1:   { Type: Schedule, Properties: { Schedule: "cron(0 14 ? * MON-FRI *)",  Input: '{"market":"US"}' } }
      USMid2:   { Type: Schedule, Properties: { Schedule: "cron(0 15 ? * MON-FRI *)",  Input: '{"market":"US"}' } }
      USMid3:   { Type: Schedule, Properties: { Schedule: "cron(0 16 ? * MON-FRI *)",  Input: '{"market":"US"}' } }
      USMid4:   { Type: Schedule, Properties: { Schedule: "cron(0 17 ? * MON-FRI *)",  Input: '{"market":"US"}' } }
      USMid5:   { Type: Schedule, Properties: { Schedule: "cron(0 18 ? * MON-FRI *)",  Input: '{"market":"US"}' } }
      USMid6:   { Type: Schedule, Properties: { Schedule: "cron(0 19 ? * MON-FRI *)",  Input: '{"market":"US"}' } }
      USMid7:   { Type: Schedule, Properties: { Schedule: "cron(30 19 ? * MON-FRI *)", Input: '{"market":"US"}' } }
      USPreClose: { Type: Schedule, Properties: { Schedule: "cron(55 19 ? * MON-FRI *)", Input: '{"market":"US"}' } }
      USClose:  { Type: Schedule, Properties: { Schedule: "cron(0 20 ? * MON-FRI *)",  Input: '{"market":"US"}' } }
    Policies:
      - DynamoDBReadPolicy:
          TableName: !Ref StockDailyTable
      - DynamoDBReadPolicy:
          TableName: !Ref StockStatsTable
      - DynamoDBReadPolicy:
          TableName: !Ref MarketIndicatorTable
      - Statement:
          - Effect: Allow
            Action: dynamodb:UpdateItem
            Resource: !GetAtt StockDailyTable.Arn
      - Statement:
          - Effect: Allow
            Action: lambda:InvokeFunction
            Resource: !GetAtt AlertingEngineFunction.Arn
```

## Security Compliance (Unit 2)

| Rule | 상태 | 비고 |
|---|---|---|
| SECURITY-01 | N/A | 신규 데이터 저장 없음 (읽기 전용) |
| SECURITY-03 | 준수 | 구조화 로깅, 스코어 결과 포함 허용 |
| SECURITY-06 | 준수 | DynamoDB 읽기 + UpdateItem + Lambda Invoke 한정 |
| SECURITY-15 | 준수 | 전역 예외 핸들러, fail-closed (0점) |
| 나머지 | N/A | 웹/네트워크/인증 없음 |
