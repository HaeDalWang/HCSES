# Unit 2: QuantAnalyzer - Code Generation Plan

## Unit Context
- **담당 기능**: FR-03, FR-04, TC-01, TC-04, TC-05, BR-01~09
- **코드 위치**: `src/quant_analyzer/`, `src/shared/scoring.py`
- **공유 모듈 재사용**: shared/models, shared/dynamodb_client, shared/market_calendar

## 생성 단계

### Step 1: 공유 모듈 — scoring.py
- [x] `src/shared/scoring.py` — Kill-Switch, Valuation, Momentum, Supply/Demand 스코어링 (Unit 4 재사용)

### Step 2: QuantAnalyzer — scoring_service.py
- [x] `src/quant_analyzer/scoring_service.py` — DynamoDB 조회 + ScoringContext 빌드 + 20거래일 누적합

### Step 3: QuantAnalyzer — handler.py
- [x] `src/quant_analyzer/handler.py` — Lambda 핸들러 (DST 검증, Kill-Switch, Bulkhead, AlertingEngine 호출)

### Step 4: template.yaml 업데이트
- [x] QuantAnalyzerKR / QuantAnalyzerUS Lambda + EventBridge 10회 스케줄 추가

### Step 5: 단위 테스트
- [x] `tests/unit/shared/test_scoring.py` — 각 스코어링 함수 검증
- [x] `tests/unit/quant_analyzer/test_scoring_service.py`
- [x] `tests/unit/quant_analyzer/test_handler.py`

### Step 6: 코드 요약
- [x] `aidlc-docs/construction/unit2-quant-analyzer/code/code-summary.md`
