# HCSES - Unit Dependency Matrix

## 유닛 간 의존성

| 유닛 | 의존 유닛 | 의존 유형 | 설명 |
|---|---|---|---|
| Unit 2: QuantAnalyzer | Unit 1: DataCollector | 데이터 의존 | `data_status=COMPLETE` 레코드 필요 |
| Unit 3: AlertingEngine | Unit 2: QuantAnalyzer | 런타임 호출 | Lambda Invoke (동기) |
| Unit 4: Backtesting | Unit 1 (로직) | 코드 공유 | `shared/scoring.py` 재사용 |
| Unit 4: Backtesting | Unit 1 (인프라) | 데이터 쓰기 | StockStatsTable Seed 마이그레이션 |

## 공유 모듈 의존성

| 모듈 | 사용 유닛 |
|---|---|
| `shared/scoring.py` | Unit 2, Unit 4 |
| `shared/market_calendar.py` | Unit 1, Unit 2 |
| `shared/dynamodb_client.py` | Unit 1, Unit 2, Unit 3, Unit 4 |
| `shared/secrets_cache.py` | Unit 1, Unit 3 |
| `shared/models.py` | 전체 |

## 배포 순서

```
1. shared/ 모듈 (공통 레이어)
2. Unit 1: DataCollector + StatsUpdater  ← DynamoDB 테이블 생성 포함
3. Unit 4: Backtesting (Seed Data 마이그레이션)  ← StockStatsTable 초기값 필요
4. Unit 2: QuantAnalyzer  ← StockStatsTable 데이터 필요
5. Unit 3: AlertingEngine  ← Unit 2 호출 대상
```

## 개발 순서 권고

Unit 1 → Unit 4 (Seed 생성) → Unit 2 → Unit 3

Unit 4를 Unit 2 이전에 실행하여 StockStatsTable에 초기 통계값을 채운 후 실제 분석 시작.
