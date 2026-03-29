# HCSES - Integration Test Instructions

## 목적
유닛 간 데이터 흐름과 상태 전이를 검증합니다.

## 사전 조건
- AWS 계정 접근 가능 (DynamoDB 테이블 생성 완료)
- `sam deploy` 완료 또는 로컬 DynamoDB (`sam local start-api`)

## 시나리오 1: DataCollector → QuantAnalyzer 데이터 흐름

### 검증 항목
1. DataCollector가 `data_status=COMPLETE` 레코드를 정상 저장하는지
2. QuantAnalyzer가 `data_status=COMPLETE AND analysis_status=PENDING` 레코드만 조회하는지
3. 분석 완료 후 `analysis_status=DONE` 업데이트 확인
4. 이미 DONE인 레코드는 재분석 skip 확인

### 테스트 방법
```bash
# 1. DataCollector 수동 실행
aws lambda invoke --function-name hcses-data-collector-kr \
  --payload '{"market":"KR"}' output.json

# 2. DynamoDB 레코드 확인
aws dynamodb get-item --table-name hcses-stock-daily \
  --key '{"ticker":{"S":"005930.KS"},"date":{"S":"2026-03-29"}}'
# → data_status=COMPLETE, analysis_status=PENDING 확인

# 3. QuantAnalyzer 수동 실행
aws lambda invoke --function-name hcses-quant-analyzer-kr \
  --payload '{"market":"KR"}' output.json

# 4. analysis_status=DONE 확인
aws dynamodb get-item --table-name hcses-stock-daily \
  --key '{"ticker":{"S":"005930.KS"},"date":{"S":"2026-03-29"}}'
```

## 시나리오 2: QuantAnalyzer → AlertingEngine 알람 발송

### 검증 항목
1. score >= 90 시 AlertingEngine Lambda 호출 확인
2. Discord 메시지 수신 확인 (테스트 채널)
3. 알람 실패 시 analysis_status=PENDING 유지 확인

### 테스트 방법
```bash
# AlertingEngine 직접 호출 (테스트 페이로드)
aws lambda invoke --function-name hcses-alerting-engine \
  --payload '{
    "ticker":"005930.KS","market":"KR","date":"2026-03-29",
    "current_price_value":75000,
    "pbr_median_value":1.2,"pbr_min_value":0.4,
    "breakdown":{"total_score":100,"valuation_score":40,
    "momentum_score":30,"supply_demand_score":30,
    "signals":["ValuationFloor","MomentumPivot","SupplyDemand"],
    "pbr_value":0.55}
  }' output.json
# → Discord 테스트 채널에서 메시지 수신 확인
```

## 시나리오 3: Backtesting → StockStatsTable Seed 마이그레이션

### 검증 항목
1. Seed Data가 StockStatsTable에 정상 저장되는지
2. CONSERVATIVE_FACTOR=1.2 적용 확인
3. QuantAnalyzer가 Seed Data를 정상 참조하는지

### 테스트 방법
```bash
# Seed 생성
PYTHONPATH=. python -m src.backtesting.backtest_runner \
  --tickers 005930.KS --market KR \
  --start 2018-01-01 --end 2025-12-31 --seed

# DynamoDB 확인
aws dynamodb get-item --table-name hcses-stock-stats \
  --key '{"ticker":{"S":"005930.KS"},"stat_type":{"S":"PBR_STATS"}}'
```

## 시나리오 4: Kill-Switch 동작 검증

### 검증 항목
1. VIX > 30 시 QuantAnalyzer 조기 종료 확인
2. stale 지표 시 VIX > 25 기준 적용 확인
3. Kill-Switch 활성 시 알람 미발송 확인
