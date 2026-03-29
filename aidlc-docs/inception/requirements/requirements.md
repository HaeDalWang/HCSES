# HCSES 요구사항 문서
# High-Confidence Stock Entry Scanner

## 인텐트 분석 요약

- **사용자 요청**: 과거 데이터 기반 저평가(Valuation Floor)와 기술적 반등(Momentum Pivot)이 합치되는 시점을 포착하여 월 1~2회 고확신 알람을 송출하는 시스템 구축
- **요청 유형**: 신규 시스템 구축 (Greenfield)
- **범위 추정**: 시스템 전체 (Data Collector + Quant Analyzer + Alerting Engine + Backtesting)
- **복잡도 추정**: Complex (AWS SAM 인프라 + 퀀트 로직 + 이중 시장 지원 + 외부 API 연동)

---

## 1. 기능 요구사항 (Functional Requirements)

### FR-01: 대상 종목 관리
- 한국 시장(KOSPI, KOSDAQ)과 미국 시장(NYSE, NASDAQ) 종목을 모두 지원
- 모니터링 종목 수: 50종목 이하 (소규모)
- 종목 목록은 설정 파일(DynamoDB 또는 환경변수)로 관리

### FR-02: Data Collector (Daily Cron)
- **수집 데이터**:
  - 종목별 OHLCV (Adjusted Close 필수 사용)
  - PBR, PER
  - RSI(14)
  - 한국 시장 한정: 외국인/기관 순매수 데이터 (FinanceDataReader)
- **시장 지표**:
  - VIX (CBOE Volatility Index)
  - US 10Y Treasury Yield
  - 원/달러 환율 (KRW/USD)
- **저장**: DynamoDB `StockDailyTable`
- **API Rate Limiting**: yfinance 호출 간 `random.uniform(1, 3)` sleep 적용
- **공휴일/휴장일 처리**: Lambda는 실행하되 데이터 없으면 graceful skip (None 체크 후 조기 종료)

### FR-03: Quant Analyzer (장 중 분산 실행)
- **실행 주기**: 한국/미국 시장 개장 시간(09:00~15:30 KST / 22:30~05:00 KST) 내 전략적 분산 실행
- **Valuation Floor 로직**:
  - 최근 5~10년 PBR 데이터 스캔 → `Min(PBR)` 산출
  - 조건: `현재 PBR ≤ Min(PBR) × 1.1`
- **Global Kill-Switch** (가중치와 별개, 활성화 시 최종 Score 강제 0점):
  - VIX > 30
  - US 10Y Yield 전일 대비 3% 급등
  - 원/달러 환율이 상단 볼린저 밴드 돌파
- **Momentum Pivot 로직**:
  - `Price > MA20` AND `RSI(14)`가 30 이하에서 35 위로 돌파

### FR-04: 스코어링 시스템 (시장별 차등 적용)

#### 한국 시장 (KR) - 100점 만점
| 지표 | 가중치 | 조건 |
|---|---|---|
| Valuation Floor (PBR) | 40점 | 현재 PBR ≤ Min(PBR) × 1.1 |
| Momentum Pivot (RSI/MA) | 30점 | Price > MA20 AND RSI 30→35 돌파 |
| Supply/Demand (수급) | 30점 | 외국인+기관 20거래일 누적 순매수합 > 0 전환 |
| **알람 임계값** | **90점 이상** | Global Kill-Switch 미활성화 시 |

#### 미국 시장 (US) - 100점 만점
| 지표 | 가중치 | 조건 |
|---|---|---|
| Valuation Floor (PBR) | 60점 | 현재 PBR ≤ Min(PBR) × 1.1 |
| Momentum Pivot (RSI/MA) | 40점 | Price > MA20 AND RSI 30→35 돌파 |
| **알람 임계값** | **90점 이상** | Global Kill-Switch 미활성화 시 |

> **보수적 원칙**: 조건이 하나라도 모호하면 True가 아닌 False 반환

### FR-05: Alerting Engine
- **알람 채널**: Discord Webhook (Telegram 대신)
- **알람 조건**: 최종 Score ≥ 90점 AND Global Kill-Switch 미활성화
- **알람 메시지 포함 내용**:
  - 종목명 / 티커
  - 현재가
  - 목표가 (PBR Median 기반)
  - 손절가 (PBR Min 기반)
  - 감지된 시그널 리스트
  - 최종 스코어 및 각 지표별 점수

### FR-06: 백테스팅 스크립트
- 과거 특정 기간(예: 2022년 하락장)에 알람 발생 여부 검증
- 알람 발생 후 3~5개월 수익률 계산
- 독립 실행 가능한 Python 스크립트로 구현

---

## 2. 비기능 요구사항 (Non-Functional Requirements)

### NFR-01: 인프라
- **플랫폼**: AWS SAM (Lambda, DynamoDB, EventBridge, Secrets Manager)
- **리전**: ap-northeast-2 (서울), 단일 계정
- **언어**: Python 3.12

### NFR-02: 데이터 품질
- Adjusted Close 가격만 사용 (배당/액면분할 반영)
- 수정 주가 미지원 데이터 소스 사용 금지

### NFR-03: 비용 최적화
- **Raw Data (StockDailyTable)**: TTL 180일 (6개월)
- **Stats Data (StockStatsTable)**: 역사적 Min/Max PBR 등 통계값 영구 보존 (별도 테이블)

### NFR-04: 보안
- Security Extension 전체 적용 (프로덕션 수준)
- API 키, Discord Webhook URL, AWS 자격증명 모두 Secrets Manager 관리
- 소스코드 내 하드코딩 자격증명 금지

### NFR-05: 신뢰성
- 공휴일/휴장일 graceful skip (크래시 없음)
- 외부 API 실패 시 재시도 로직 (최대 3회)
- 모든 외부 호출에 명시적 예외 처리

### NFR-06: 관찰 가능성
- 구조화된 로깅 (timestamp, correlation ID, log level, message)
- CloudWatch Logs 연동
- 민감 데이터(토큰, 키) 로그 출력 금지

---

## 3. 데이터 라이브러리 매핑

| 데이터 | 라이브러리 | 비고 |
|---|---|---|
| 한국/미국 OHLCV, PBR, PER, RSI | yfinance | Adjusted Close 필수 |
| 한국 외국인/기관 순매수 | FinanceDataReader | 한국 시장 전용 |
| VIX, US10Y Yield | pandas_datareader | FRED 데이터 소스 |
| 원/달러 환율 | yfinance (KRW=X) | 볼린저 밴드 계산 포함 |

---

## 4. DynamoDB 테이블 설계 (초안)

| 테이블명 | 파티션 키 | 정렬 키 | TTL | 용도 |
|---|---|---|---|---|
| StockDailyTable | ticker | date | 180일 | 일별 OHLCV/지표 Raw Data. `data_status` (`COLLECTING`/`COMPLETE`/`FAILED`) + `analysis_status` (`PENDING`/`DONE`) 필드 포함. 수치 소수점 4자리 정규화 |
| StockStatsTable | ticker | stat_type | 없음 (영구) | 역사적 Min/Max/Median PBR 등 통계. 매주 토요일 업데이트 |
| MarketIndicatorTable | indicator | date | 180일 | VIX, US10Y, 환율 |

---

## 5. 제약사항 및 가정

- yfinance는 비공식 API이므로 Rate Limiting 필수 적용
- 미국 시장 수급 데이터 미지원 (13F 분기 지연 공시로 실시간 불가)
- 백테스팅은 별도 스크립트로 운영 시스템과 분리
- 알람 빈도 목표: 월 1~2회 (고확신 필터링)

---

## 6. 기술적 제약 (Technical Constraints)

### TC-01: 멱등성 (Idempotency)
- 동일 날짜 + 동일 타임스탬프의 분석 요청이 중복 실행되어도 DynamoDB에 중복 데이터 생성 금지
- DynamoDB 쓰기 시 `ConditionExpression`으로 중복 방지 또는 `PutItem`의 조건부 쓰기 사용

### TC-02: Secret Caching
- Lambda 실행 컨텍스트 내 전역 변수(Global Variable) 공간에 Secrets Manager 응답 캐싱
- 동일 컨텍스트 재사용 시 API 재호출 금지 (콜드 스타트 시에만 호출)

### TC-03: Discord Payload Limit
- Discord Webhook 메시지 2,000자 제한 초과 시 메시지 분할 또는 요약 처리
- 초과 감지 후 예외 처리 로직 필수 포함

### TC-04: 시장별 EventBridge 스케줄 분리
- 한국 시장(KR)과 미국 시장(US) EventBridge Cron을 별도 트리거로 분리 정의
- 미국 시장: 서머타임(DST) 적용 여부에 따라 UTC 기준 실행 시간 변동
  - EDT (3월~11월): UTC-4 → 미국 장 시작 13:30 UTC
  - EST (11월~3월): UTC-5 → 미국 장 시작 14:30 UTC
- Lambda 내부에서 현재 날짜 기준 DST 적용 여부 감지 로직 포함 (`pytz` 또는 `zoneinfo` 사용)

### TC-05: Data Race Condition 방지
- `StockDailyTable`에 `data_status` 필드 추가: `COLLECTING` | `COMPLETE` | `FAILED`
- QuantAnalyzer는 `data_status = 'COMPLETE'`인 레코드만 참조
- DataCollector 완료 시 해당 날짜 레코드의 `data_status`를 `COMPLETE`로 업데이트

### TC-06: StockStatsTable 업데이트 주기
- 정기 업데이트: 매주 토요일 (주간 배치)
- 이벤트 기반 업데이트: 분기 실적 발표 후 수동 트리거 가능
- Backtesting 스크립트(Unit 4)가 생성한 통계값을 StockStatsTable 초기값(Seed Data)으로 마이그레이션하는 단계를 Construction Phase에 포함

---

## 7. 엔지니어링 원칙 (Engineering Constraints)

## EC-01: 한국 시장 PBR 결측 처리
- yfinance에서 한국 종목 PBR 데이터가 결측(None/NaN)인 경우 대체 데이터 소스 순서대로 시도:
  1. FinanceDataReader PBR 데이터
  2. KRX 공시 데이터 (직접 파싱)
- 모든 소스에서 결측 시 해당 종목은 Valuation Floor 점수 0점 처리 (False 반환, 크래시 금지)
- 결측 발생 시 CloudWatch에 경고 로그 기록

### EC-02: 절대값 vs 상대적 변동률 명확 구분
- 모든 계산 함수에서 변수명으로 의도를 명시:
  - 절대 수치: `_value`, `_price`, `_level` 접미사 (예: `pbr_value`, `rsi_level`)
  - 상대적 변동률: `_pct`, `_ratio`, `_change` 접미사 (예: `yield_change_pct`, `volume_ratio`)
- 두 유형을 혼용하는 연산은 명시적 변환 함수를 통해서만 수행
- 코드 리뷰 체크리스트 항목으로 포함
