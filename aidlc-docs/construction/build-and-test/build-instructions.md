# HCSES - Build Instructions

## Prerequisites
- Python 3.12
- AWS CLI v2 (configured with `ap-northeast-2`)
- AWS SAM CLI >= 1.100
- pip / virtualenv
- Docker (SAM build용)

## Build Steps

### 1. 가상환경 생성 및 의존성 설치
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov  # 테스트용
```

### 2. Lambda Layer 의존성 준비
```bash
mkdir -p dependencies/python
pip install -r requirements.txt -t dependencies/python/
```

### 3. SAM Build
```bash
sam build --use-container
```

### 4. SAM Validate
```bash
sam validate --lint
```

### 5. Build 성공 확인
- `.aws-sam/build/` 디렉토리에 각 Lambda 함수 빌드 결과 확인
- `template.yaml` 파싱 오류 없음 확인

## 환경변수 (로컬 테스트용)
```bash
export STOCK_DAILY_TABLE=hcses-stock-daily
export STOCK_STATS_TABLE=hcses-stock-stats
export MARKET_INDICATOR_TABLE=hcses-market-indicator
export MARKET=KR
export DISCORD_SECRET_NAME=hcses/discord-webhook-url
export AWS_REGION=ap-northeast-2
```

## Secrets Manager 사전 설정 (수동)
```bash
aws secretsmanager create-secret \
  --name hcses/discord-webhook-url \
  --secret-string '{"webhook_url":"https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"}' \
  --region ap-northeast-2
```

## SAM Deploy
```bash
sam deploy --guided  # 최초
sam deploy           # 이후
```
