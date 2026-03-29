# HCSES - Unit of Work Story Map

## 기능 요구사항 → 유닛 매핑

| 요구사항 ID | 설명 | 담당 유닛 |
|---|---|---|
| FR-01 | 대상 종목 관리 | Unit 1 |
| FR-02 | Data Collector (OHLCV, PBR, 수급, 시장지표) | Unit 1 |
| FR-03 | Quant Analyzer (Kill-Switch, Valuation, Momentum) | Unit 2 |
| FR-04 | 스코어링 시스템 (KR/US 차등) | Unit 2 (shared/scoring.py) |
| FR-05 | Alerting Engine (Discord, 목표가/손절가) | Unit 3 |
| FR-06 | 백테스팅 스크립트 | Unit 4 |

## 기술적 제약 → 유닛 매핑

| 제약 ID | 설명 | 담당 유닛 |
|---|---|---|
| TC-01 | 멱등성 | Unit 1, Unit 2 |
| TC-02 | Secret Caching | Unit 1, Unit 3 |
| TC-03 | Discord 2,000자 제한 | Unit 3 |
| TC-04 | EventBridge DST 분리 | Unit 1, Unit 2 |
| TC-05 | data_status Race Condition 방지 | Unit 1, Unit 2 |
| TC-06 | StockStatsTable 주간 업데이트 + Seed | Unit 1 (StatsUpdater), Unit 4 |

## 엔지니어링 제약 → 유닛 매핑

| 제약 ID | 설명 | 담당 유닛 |
|---|---|---|
| EC-01 | KR PBR 결측 fallback | Unit 1, Unit 4 |
| EC-02 | 절대값/변동률 변수명 구분 | 전체 |
| 정규화 | 소수점 4자리 | Unit 1 |
| analysis_status | 재계산 방지 | Unit 2 |
| FDR 캐시 | KR PBR 백테스팅 결측 | Unit 4 |
