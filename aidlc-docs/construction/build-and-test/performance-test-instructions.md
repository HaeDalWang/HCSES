# HCSES - Performance Test Instructions

## 성능 요구사항

| Lambda | 메모리 | 타임아웃 | 예상 실행 시간 | 일일 호출 |
|---|---|---|---|---|
| DataCollectorKR/US | 512MB | 900초 | 5~8분 (50종목) | 2회 |
| QuantAnalyzerKR/US | 256MB | 300초 | 1~3분 (50종목) | 20회 |
| AlertingEngine | 128MB | 30초 | 2~5초 | 0~2회 |
| StatsUpdater | 256MB | 300초 | 3~5분 (10종목) | 1회/주 |

## 테스트 1: DataCollector 실행 시간 측정

```bash
# 시간 측정 포함 실행
time aws lambda invoke --function-name hcses-data-collector-kr \
  --payload '{"market":"KR"}' output.json

# 기대: 900초 이내 완료
# Rate Limiting (1~3초/종목) 포함 50종목 → 최대 150초 + API 응답 시간
```

## 테스트 2: QuantAnalyzer 실행 시간 측정

```bash
time aws lambda invoke --function-name hcses-quant-analyzer-kr \
  --payload '{"market":"KR"}' output.json

# 기대: 300초 이내 완료
# DynamoDB 조회 위주 → 50종목 × 최대 5초 = 250초
```

## 테스트 3: DynamoDB 읽기/쓰기 지연

```bash
# CloudWatch Metrics 확인
# StockDailyTable: SuccessfulRequestLatency < 10ms (PAY_PER_REQUEST)
# 쓰기 용량: 50종목 × 1 WCU = 50 WCU/실행
```

## 테스트 4: yfinance Rate Limiting 효과

```bash
# CloudWatch Logs에서 sleep 간격 확인
# 기대: 종목 간 1~3초 sleep 적용 → IP 차단 없음
# 모니터링: 연속 5회 이상 empty_data_skip 발생 시 Rate Limiting 조정 필요
```

## 비용 추정 (월간)

| 항목 | 계산 | 예상 비용 |
|---|---|---|
| Lambda (DataCollector) | 2회/일 × 30일 × 512MB × 480초 | ~$0.50 |
| Lambda (QuantAnalyzer) | 20회/일 × 22일 × 256MB × 180초 | ~$0.80 |
| Lambda (AlertingEngine) | ~2회/월 × 128MB × 5초 | ~$0.00 |
| Lambda (StatsUpdater) | 4회/월 × 256MB × 300초 | ~$0.01 |
| DynamoDB (PAY_PER_REQUEST) | ~3000 WCU + 50000 RCU/월 | ~$1.50 |
| Secrets Manager | 1 secret × ~20 호출/월 | ~$0.40 |
| **합계** | | **~$3.21/월** |
