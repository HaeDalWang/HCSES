# HCSES 배포 및 테스트 가이드

## Step 1: 사전 준비

### 필수 도구 설치
```bash
# Python 3.12
python3.12 --version

# AWS CLI v2
aws --version

# AWS SAM CLI
sam --version
# 없으면: brew install aws-sam-cli (macOS)

# Docker (SAM build에 필요)
docker --version
```

### AWS CLI 프로파일 설정
```bash
aws configure
# AWS Access Key ID: [입력]
# AWS Secret Access Key: [입력]
# Default region name: ap-northeast-2
# Default output format: json

# 설정 확인
aws sts get-caller-identity
```

---

## Step 2: 프로젝트 의존성 설치

```bash
# 가상환경 생성
python3.12 -m venv .venv
source .venv/bin/activate

# 개발 의존성 설치
pip install -r requirements.txt
pip install pytest pytest-cov
```

---

## Step 3: 단위 테스트 실행 (배포 전 검증)

```bash
PYTHONPATH=. pytest tests/unit/ -v --tb=short
```

전체 통과 확인 후 다음 단계로 진행합니다.

---

## Step 4: Lambda Layer 준비

SAM은 외부 라이브러리를 Layer로 패키징합니다.

```bash
mkdir -p dependencies/python
pip install -r requirements.txt -t dependencies/python/
```

---

## Step 5: SAM Build

```bash
sam build --use-container
```

`.aws-sam/build/` 디렉토리에 각 Lambda 함수가 빌드됩니다.
빌드 오류 시 `sam validate --lint`로 template.yaml 문법을 확인하세요.

---

## Step 6: SAM Deploy (최초 배포)

```bash
sam deploy --guided
```

프롬프트에 다음과 같이 입력합니다:

```
Stack name: hcses
AWS Region: ap-northeast-2
Confirm changes before deploy: y
Allow SAM CLI IAM role creation: y
Disable rollback: n
Save arguments to configuration file: y
SAM configuration file: samconfig.toml
SAM configuration environment: default
```

배포 완료 후 출력되는 리소스 ARN을 확인합니다:
- `StockDailyTableName`
- `StockStatsTableName`
- `MarketIndicatorTableName`
- `AlertingEngineArn`

---

## Step 7: Discord Webhook 설정

### 7-1. Discord 서버에서 Webhook 생성
1. Discord 서버 → 채널 설정 → 연동 → 웹후크
2. "새 웹후크" 클릭 → 이름: `HCSES Alert`
3. 웹후크 URL 복사

### 7-2. AWS Secrets Manager에 저장
```bash
aws secretsmanager create-secret \
  --name hcses/discord-webhook-url \
  --secret-string '{"webhook_url":"여기에_복사한_웹후크_URL_붙여넣기"}' \
  --region ap-northeast-2
```

---

## Step 8: Backtesting + Seed Data 생성

StockStatsTable에 PBR 통계 초기값을 채워야 QuantAnalyzer가 정상 동작합니다.

```bash
source .venv/bin/activate

# KR 종목 Seed 생성 (5~7년 데이터)
PYTHONPATH=. python -m src.backtesting.backtest_runner \
  --tickers 005930.KS 000660.KS 035420.KS 051910.KS 006400.KS \
  --market KR \
  --start 2019-01-01 \
  --end 2025-12-31 \
  --seed

# US 종목 Seed 생성
PYTHONPATH=. python -m src.backtesting.backtest_runner \
  --tickers AAPL MSFT GOOGL AMZN META \
  --market US \
  --start 2019-01-01 \
  --end 2025-12-31 \
  --seed
```

Seed 저장 확인:
```bash
aws dynamodb get-item \
  --table-name hcses-stock-stats \
  --key '{"ticker":{"S":"005930.KS"},"stat_type":{"S":"PBR_STATS"}}' \
  --region ap-northeast-2
```

`pbr_min_value`, `pbr_median_value`, `pbr_max_value`가 출력되면 성공입니다.

---

## Step 9: DataCollector 수동 Invoke 테스트

### 9-1. KR 시장 수집
```bash
aws lambda invoke \
  --function-name hcses-data-collector-kr \
  --payload '{"market":"KR"}' \
  --cli-binary-format raw-in-base64-out \
  --region ap-northeast-2 \
  /tmp/dc-kr-output.json

cat /tmp/dc-kr-output.json
```

기대 결과: `{"statusCode": 200, "body": "{\"success\":[...],\"failed\":[],\"skipped\":[]}"}`

### 9-2. 저장된 데이터 확인
```bash
aws dynamodb get-item \
  --table-name hcses-stock-daily \
  --key '{"ticker":{"S":"005930.KS"},"date":{"S":"2026-03-29"}}' \
  --region ap-northeast-2
```

`data_status: COMPLETE`, `analysis_status: PENDING` 확인.

### 9-3. US 시장 수집
```bash
aws lambda invoke \
  --function-name hcses-data-collector-us \
  --payload '{"market":"US"}' \
  --cli-binary-format raw-in-base64-out \
  --region ap-northeast-2 \
  /tmp/dc-us-output.json

cat /tmp/dc-us-output.json
```

### 9-4. 시장 지표 확인
```bash
aws dynamodb get-item \
  --table-name hcses-market-indicator \
  --key '{"indicator":{"S":"VIX"},"date":{"S":"2026-03-29"}}' \
  --region ap-northeast-2
```

---

## Step 10: QuantAnalyzer 수동 Invoke 테스트

DataCollector 실행 후 진행합니다.

```bash
aws lambda invoke \
  --function-name hcses-quant-analyzer-kr \
  --payload '{"market":"KR"}' \
  --cli-binary-format raw-in-base64-out \
  --region ap-northeast-2 \
  /tmp/qa-kr-output.json

cat /tmp/qa-kr-output.json
```

기대 결과: `{"statusCode": 200, "body": "{\"alerted\":[],\"analyzed\":[...],\"skipped\":[]}"}`

`analysis_status` 변경 확인:
```bash
aws dynamodb get-item \
  --table-name hcses-stock-daily \
  --key '{"ticker":{"S":"005930.KS"},"date":{"S":"2026-03-29"}}' \
  --region ap-northeast-2 \
  --projection-expression "analysis_status"
```

`analysis_status: DONE` 확인.

---

## Step 11: AlertingEngine 수동 Invoke 테스트

실제 Discord 메시지 수신을 확인합니다.

```bash
aws lambda invoke \
  --function-name hcses-alerting-engine \
  --payload '{
    "ticker": "005930.KS",
    "market": "KR",
    "date": "2026-03-29",
    "current_price_value": 75000,
    "pbr_median_value": 1.2,
    "pbr_min_value": 0.4,
    "breakdown": {
      "total_score": 100,
      "valuation_score": 40,
      "momentum_score": 30,
      "supply_demand_score": 30,
      "signals": ["ValuationFloor: PBR(0.55)<=MinPBR*1.1(0.55)", "MomentumPivot: RSI 28->36", "SupplyDemand: 양전 전환"],
      "pbr_value": 0.55
    }
  }' \
  --cli-binary-format raw-in-base64-out \
  --region ap-northeast-2 \
  /tmp/ae-output.json

cat /tmp/ae-output.json
```

Discord 채널에서 알람 메시지가 수신되면 성공입니다.

---

## Step 12: StatsUpdater 수동 Invoke 테스트

```bash
aws lambda invoke \
  --function-name hcses-stats-updater \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  --region ap-northeast-2 \
  /tmp/su-output.json

cat /tmp/su-output.json
```

---

## Step 13: CloudWatch Logs 확인

각 Lambda의 실행 로그를 확인합니다.

```bash
# DataCollector KR 로그
aws logs tail /aws/lambda/hcses-data-collector-kr --since 1h --region ap-northeast-2

# QuantAnalyzer KR 로그
aws logs tail /aws/lambda/hcses-quant-analyzer-kr --since 1h --region ap-northeast-2

# AlertingEngine 로그
aws logs tail /aws/lambda/hcses-alerting-engine --since 1h --region ap-northeast-2
```

---

## Step 14: EventBridge 스케줄 확인

배포 후 EventBridge 규칙이 자동 생성됩니다.

```bash
aws events list-rules --name-prefix hcses --region ap-northeast-2
```

스케줄이 활성화되면 다음 시간부터 자동 실행됩니다:
- KR DataCollector: 매일 16:30 KST (07:30 UTC)
- US DataCollector: 매일 06:30 KST (21:30 UTC)
- KR QuantAnalyzer: 장 중 10회 (09:00~15:20 KST)
- US QuantAnalyzer: 장 중 10회 (EDT 09:30~16:00)
- StatsUpdater: 매주 토요일 09:00 KST (00:00 UTC)

---

## 문제 해결

### Lambda 타임아웃
- DataCollector가 900초 초과 시 종목 수를 줄이거나 Rate Limiting sleep을 조정

### yfinance IP 차단
- CloudWatch에서 연속 `empty_data_skip` 확인
- sleep 간격을 `random.uniform(2, 5)`로 상향 조정

### Discord 알람 미수신
- Secrets Manager에 `webhook_url` 키가 정확한지 확인
- AlertingEngine CloudWatch 로그에서 `discord_alert_failed` 검색

### PBR 데이터 결측
- CloudWatch에서 `pbr_missing` WARNING 로그 확인
- KR 종목: FinanceDataReader fallback 동작 여부 확인

---

## 스택 삭제 (정리)

```bash
sam delete --stack-name hcses --region ap-northeast-2
```

DynamoDB 테이블과 Lambda 함수가 모두 삭제됩니다.
Secrets Manager는 별도 삭제가 필요합니다:
```bash
aws secretsmanager delete-secret \
  --secret-id hcses/discord-webhook-url \
  --force-delete-without-recovery \
  --region ap-northeast-2
```
