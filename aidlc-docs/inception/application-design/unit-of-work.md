# HCSES - Units of Work

## 분해 전략
- 각 유닛은 독립적으로 배포 가능한 Lambda 함수 또는 독립 실행 스크립트
- 유닛 간 결합은 DynamoDB 상태 필드(`data_status`, `analysis_status`)와 Lambda Invoke로만 연결
- 공유 비즈니스 로직은 `shared/` 모듈로 분리하여 코드 중복 방지

---

## Unit 1: DataCollector

**설명**: 한국/미국 종목 및 시장 지표 데이터를 수집하여 DynamoDB에 저장하는 일별 배치 Lambda

**컴포넌트**: DataCollector, StatsUpdater (부속)

**책임**:
- 종목별 OHLCV (Adjusted Close), PBR, PER, RSI(14) 수집
- 한국 시장 외국인/기관 순매수 수집 (FinanceDataReader)
- 시장 지표 수집 (VIX, US10Y, KRW/USD)
- 수치 정규화 (소수점 4자리)
- DynamoDB 저장 (`data_status`: COLLECTING → COMPLETE/FAILED)
- 멱등성 보장, Rate Limiting, 공휴일 graceful skip
- StatsUpdater: 매주 토요일 PBR 통계 갱신

**산출물**:
- `src/data_collector/handler.py`
- `src/data_collector/ingestion_service.py`
- `src/stats_updater/handler.py`
- `shared/market_calendar.py`
- `shared/dynamodb_client.py`
- `shared/models.py`
- `shared/secrets_cache.py`

**트리거**:
- KR Collector: EventBridge `cron(30 7 * * ? *)` (UTC, 평일)
- US Collector: EventBridge `cron(30 13 * * ? *)` (UTC EDT) / `cron(30 14 * * ? *)` (UTC EST)
- StatsUpdater: EventBridge `cron(0 0 ? * SAT *)` (UTC)

---

## Unit 2: QuantAnalyzer

**설명**: 수집된 데이터를 기반으로 종목별 스코어를 산출하고 알람 후보를 식별하는 장 중 분산 실행 Lambda

**컴포넌트**: QuantAnalyzer

**책임**:
- DST 감지 및 시장 운영 시간 검증
- Global Kill-Switch 평가
- Valuation Floor / Momentum Pivot / Supply/Demand 스코어링
- 시장별 차등 가중치 적용 (KR/US)
- `analysis_status` 관리 (재계산 방지)
- 90점 이상 종목 AlertingEngine 호출

**산출물**:
- `src/quant_analyzer/handler.py`
- `src/quant_analyzer/scoring_service.py`
- `shared/scoring.py`

**트리거**:
- KR Analyzer: EventBridge 장 중 분산 (09:00~15:30 KST, 10회)
- US Analyzer: EventBridge 장 중 분산 (DST 반영, 10회)

---

## Unit 3: AlertingEngine

**설명**: 고확신 알람 조건 충족 종목에 대해 Discord Webhook으로 메시지를 발송하는 Lambda

**컴포넌트**: AlertingEngine

**책임**:
- 목표가/손절가 계산 (PBR Median/Min 기반)
- Discord 메시지 포맷 생성
- 2,000자 제한 처리
- Secrets Manager 캐싱
- Discord Webhook 발송 (최대 3회 재시도)

**산출물**:
- `src/alerting_engine/handler.py`
- `src/alerting_engine/alert_service.py`

**트리거**: QuantAnalyzer Lambda Invoke (동기 호출)

---

## Unit 4: Backtesting

**설명**: 과거 데이터로 알람 로직을 검증하고 StockStatsTable Seed Data를 생성하는 독립 실행 스크립트

**컴포넌트**: Backtesting

**책임**:
- 히스토리컬 데이터 로드 (yfinance + FDR 로컬 캐시 fallback)
- 동일 스코어링 로직으로 과거 알람 시뮬레이션 (`shared/scoring.py` 재사용)
- 알람 후 3/5개월 수익률 계산
- StockStatsTable Seed Data 생성 및 마이그레이션
- 결과 CSV 리포트 출력

**산출물**:
- `src/backtesting/backtest_runner.py`
- `src/backtesting/seed_migrator.py`

**트리거**: CLI 수동 실행 (`python -m src.backtesting.backtest_runner`)

---

## 코드 구조 (예상)

```
hcses/
├── src/
│   ├── data_collector/
│   │   ├── handler.py
│   │   └── ingestion_service.py
│   ├── quant_analyzer/
│   │   ├── handler.py
│   │   └── scoring_service.py
│   ├── alerting_engine/
│   │   ├── handler.py
│   │   └── alert_service.py
│   ├── stats_updater/
│   │   └── handler.py
│   ├── backtesting/
│   │   ├── backtest_runner.py
│   │   └── seed_migrator.py
│   └── shared/
│       ├── models.py
│       ├── scoring.py
│       ├── market_calendar.py
│       ├── dynamodb_client.py
│       └── secrets_cache.py
├── tests/
│   ├── unit/
│   └── integration/
├── template.yaml          # AWS SAM
├── requirements.txt
└── samconfig.toml
```
