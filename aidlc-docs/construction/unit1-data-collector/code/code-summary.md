# Unit 1: DataCollector - Code Summary

## 생성된 파일

### 프로젝트 설정
- `requirements.txt` — 의존성 버전 고정
- `samconfig.toml` — SAM 배포 설정
- `template.yaml` — SAM 템플릿 (DynamoDB 3개 테이블 + Lambda 3개)
- `.gitignore`

### 공유 모듈 (src/shared/)
- `models.py` — StockDailyRecord, MarketIndicatorRecord, StockStatsRecord, AnalysisResult
- `dynamodb_client.py` — DynamoDB 클라이언트 (멱등성 헬퍼, TTL 계산)
- `secrets_cache.py` — Secrets Manager 전역 캐싱 (TC-02)
- `market_calendar.py` — 공휴일 판별, DST 감지 (TC-04)

### DataCollector (src/data_collector/)
- `ingestion_service.py` — 수집 로직 (yfinance, FDR, pandas_datareader, RSI/MA/볼린저 계산)
- `handler.py` — Lambda 핸들러 (Bulkhead, 구조화 로깅, 전역 예외 처리)

### StatsUpdater (src/stats_updater/)
- `handler.py` — 주간 PBR 통계 재계산

### 테스트 (tests/unit/)
- `shared/test_models.py`
- `shared/test_market_calendar.py`
- `data_collector/test_ingestion_service.py` — RSI, MA20, 볼린저, 정규화, PBR fallback
- `data_collector/test_handler.py` — Bulkhead, 휴장일 skip, 전역 예외 처리

## 적용된 제약사항
- BR-01~09 전체 적용
- TC-01 (멱등성), TC-02 (Secret 캐싱), TC-04 (DST), TC-05 (data_status), TC-06 (StatsUpdater)
- EC-01 (PBR fallback), EC-02 (변수명 규칙)
- SECURITY-01, 03, 06, 09, 12, 15 준수
