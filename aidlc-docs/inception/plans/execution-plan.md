# Execution Plan - HCSES

## Detailed Analysis Summary

### Change Impact Assessment
- **User-facing changes**: Yes - Discord 알람 메시지 (알람 수신자 경험)
- **Structural changes**: Yes - 신규 시스템 전체 설계 (3개 Lambda + DynamoDB + EventBridge)
- **Data model changes**: Yes - StockDailyTable, StockStatsTable, MarketIndicatorTable 신규 설계
- **API changes**: Yes - Discord Webhook, yfinance, FinanceDataReader, pandas_datareader 연동
- **NFR impact**: Yes - 보안(Secrets Manager), 비용최적화(TTL), 신뢰성(graceful skip), 관찰가능성(CloudWatch)

### Risk Assessment
- **Risk Level**: High
- **Rollback Complexity**: Moderate (SAM 스택 삭제로 롤백 가능)
- **Testing Complexity**: Complex (퀀트 로직 검증 + 백테스팅 + AWS 인프라 통합 테스트)

---

## Workflow Visualization

```
INCEPTION PHASE
  [x] Workspace Detection        - COMPLETED
  [-] Reverse Engineering        - SKIPPED (Greenfield)
  [x] Requirements Analysis      - COMPLETED
  [-] User Stories               - SKIPPED (알람 수신자 단일 페르소나, 복잡도 대비 가치 낮음)
  [x] Workflow Planning          - IN PROGRESS
  [>] Application Design         - EXECUTE
  [>] Units Generation           - EXECUTE

CONSTRUCTION PHASE (per-unit)
  [>] Functional Design          - EXECUTE
  [>] NFR Requirements           - EXECUTE
  [>] NFR Design                 - EXECUTE
  [>] Infrastructure Design      - EXECUTE
  [>] Code Generation            - EXECUTE (ALWAYS)
  [>] Build and Test             - EXECUTE (ALWAYS)

OPERATIONS PHASE
  [ ] Operations                 - PLACEHOLDER
```

---

## Phases to Execute

### INCEPTION PHASE
- [x] Workspace Detection - COMPLETED
- [-] Reverse Engineering - SKIPPED (Greenfield)
- [x] Requirements Analysis - COMPLETED
- [-] User Stories - SKIPPED
  - **Rationale**: 알람 수신자(투자자) 단일 페르소나. 시스템이 자동화 파이프라인 중심이며 사용자 인터랙션 없음. 요구사항이 이미 충분히 구체적.
- [x] Workflow Planning - IN PROGRESS
- [ ] Application Design - EXECUTE
  - **Rationale**: 신규 시스템. 3개 Lambda 컴포넌트(DataCollector, QuantAnalyzer, AlertingEngine) + Backtesting 스크립트의 인터페이스, 메서드, 서비스 레이어 설계 필요.
- [ ] Units Generation - EXECUTE
  - **Rationale**: 4개 독립 유닛(DataCollector, QuantAnalyzer, AlertingEngine, Backtesting)으로 분해 필요. 각 유닛별 Construction Phase 실행.

### CONSTRUCTION PHASE (유닛별 반복)
- [ ] Functional Design - EXECUTE (per-unit)
  - **Rationale**: 퀀트 로직(Valuation Floor, Momentum Pivot, 수급 분석), 스코어링, 시장별 차등 로직 등 복잡한 비즈니스 로직 상세 설계 필요.
- [ ] NFR Requirements - EXECUTE (per-unit)
  - **Rationale**: 성능(Rate Limiting), 보안(Secrets Manager, Security Extension 전체), 비용(TTL), 신뢰성(graceful skip) 요구사항 존재.
- [ ] NFR Design - EXECUTE (per-unit)
  - **Rationale**: NFR Requirements 실행 예정이므로 NFR 패턴 설계 필요.
- [ ] Infrastructure Design - EXECUTE (per-unit)
  - **Rationale**: AWS SAM 인프라(Lambda, DynamoDB, EventBridge, Secrets Manager) 상세 매핑 필요.
- [ ] Code Generation - EXECUTE (ALWAYS, per-unit)
- [ ] Build and Test - EXECUTE (ALWAYS)

### OPERATIONS PHASE
- [ ] Operations - PLACEHOLDER

---

## Units of Work (확정)

| Unit | 설명 | 우선순위 |
|---|---|---|
| Unit 1: DataCollector | Daily Cron Lambda - OHLCV/지표/시장데이터 수집. `data_status` 필드 관리 | 1 |
| Unit 2: QuantAnalyzer | 시장별 분산 실행 Lambda - 스코어링 엔진. `data_status=COMPLETE` 데이터만 참조 | 2 |
| Unit 3: AlertingEngine | Discord 알람 발송 Lambda. 2,000자 제한 처리 포함 | 3 |
| Unit 4: Backtesting | 독립 실행 Python 스크립트. StockStatsTable Seed Data 마이그레이션 포함 | 4 |

---

## 기술적 제약 요약 (Construction Phase 전달 사항)

| ID | 제약 | 적용 유닛 |
|---|---|---|
| TC-01 | 멱등성 - DynamoDB 중복 쓰기 방지 | Unit 1, 2 |
| TC-02 | Secret Caching - Lambda 전역 변수 캐싱 | Unit 1, 2, 3 |
| TC-03 | Discord 2,000자 제한 예외 처리 | Unit 3 |
| TC-04 | 시장별 EventBridge 분리 + DST 감지 | Unit 2 |
| TC-05 | data_status 필드로 Race Condition 방지 | Unit 1, 2 |
| TC-06 | StockStatsTable 주간 업데이트 + Seed 마이그레이션 | Unit 1, 4 |

---

## Success Criteria
- **Primary Goal**: 월 1~2회 고확신 Discord 알람 자동 발송
- **Key Deliverables**: 4개 유닛 코드 + SAM template.yaml + 백테스팅 스크립트
- **Quality Gates**: 
  - 모든 Security Extension 규칙 준수
  - 공휴일/휴장일 graceful skip 검증
  - 백테스팅으로 2022년 하락장 검증
  - Adjusted Close 사용 검증
