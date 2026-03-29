# Unit 1: DataCollector - Code Generation Plan

## Unit Context
- **담당 기능**: FR-01, FR-02, TC-01, TC-02, TC-04, TC-05, TC-06, EC-01, EC-02
- **코드 위치**: 워크스페이스 루트 (aidlc-docs/ 제외)
- **구조 패턴**: Greenfield multi-unit monolith → `src/{unit}/`, `tests/{unit}/`
- **공유 모듈**: `src/shared/` (Unit 2, 3, 4와 공유)

## 생성 단계

### Step 1: 프로젝트 구조 및 공통 설정 파일
- [x] `requirements.txt`
- [x] `samconfig.toml`
- [x] `template.yaml`
- [x] `.gitignore`
- [x] `src/__init__.py`

### Step 2: 공유 모듈 — models.py
- [x] `src/shared/models.py`

### Step 3: 공유 모듈 — dynamodb_client.py
- [x] `src/shared/dynamodb_client.py`

### Step 4: 공유 모듈 — secrets_cache.py
- [x] `src/shared/secrets_cache.py`

### Step 5: 공유 모듈 — market_calendar.py
- [x] `src/shared/market_calendar.py`

### Step 6: DataCollector — ingestion_service.py
- [x] `src/data_collector/ingestion_service.py`

### Step 7: DataCollector — handler.py
- [x] `src/data_collector/handler.py`

### Step 8: StatsUpdater — handler.py
- [x] `src/stats_updater/handler.py`

### Step 9: 단위 테스트 — shared 모듈
- [x] `tests/unit/shared/test_models.py`
- [x] `tests/unit/shared/test_market_calendar.py`

### Step 10: 단위 테스트 — DataCollector
- [x] `tests/unit/data_collector/test_ingestion_service.py`
- [x] `tests/unit/data_collector/test_handler.py`

### Step 11: 코드 요약 문서
- [x] `aidlc-docs/construction/unit1-data-collector/code/code-summary.md`
