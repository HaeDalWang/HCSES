# HCSES - High-Confidence Stock Entry Scanner

## Project Overview

AWS SAM 기반 서버리스 퀀트 스캐너. KR/US 시장 주식의 매수 진입 시점을 스코어링하여 알림 발송.

## Tech Stack

- **Language**: Python 3.12
- **Infrastructure**: AWS SAM (Lambda, DynamoDB, EventBridge)
- **Architecture**: arm64 Lambda functions
- **Region**: ap-northeast-2

## Project Structure

```
src/
├── data_collector/    # 시장 데이터 수집 (yfinance)
├── quant_analyzer/    # 퀀트 스코어링 엔진
├── stats_updater/     # 역사 통계 갱신
├── alerting_engine/   # 알림 발송
├── backtesting/       # 백테스트
└── shared/            # 공통 모듈 (models, scoring, dynamodb_client)

tests/
├── unit/              # 단위 테스트
└── integration/       # 통합 테스트
```

## Commands

```bash
# Build
sam build

# Deploy
sam deploy

# Test
pytest tests/unit/ -v
pytest tests/integration/ -v

# Local invoke
sam local invoke DataCollectorKR --event events/kr.json
```

## Key Conventions

- Lambda handler 패턴: `src/<module>/handler.py`
- 비즈니스 로직은 `*_service.py`에 분리
- 공유 코드는 `src/shared/`
- DynamoDB 테이블: StockDaily, StockStats, MarketIndicator
- 환경변수로 테이블명 전달 (template.yaml에서 정의)
