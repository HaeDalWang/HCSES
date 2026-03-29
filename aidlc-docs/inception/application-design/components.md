# HCSES - Component Definitions

## Component 1: DataCollector

**목적**: 대상 종목 및 시장 지표 데이터를 수집하여 DynamoDB에 저장

**책임**:
- 종목 목록 로드 (설정 소스에서)
- 한국/미국 종목 OHLCV (Adjusted Close) 수집
- PBR, PER, RSI(14) 수집
- 한국 시장 한정 외국인/기관 순매수 수집
- 시장 지표(VIX, US10Y Yield, KRW/USD 환율) 수집
- Rate Limiting 적용 (random.uniform(1,3) sleep)
- 공휴일/휴장일 graceful skip
- DynamoDB StockDailyTable 저장 (data_status: COLLECTING → COMPLETE/FAILED)
- DynamoDB MarketIndicatorTable 저장
- 멱등성 보장 (중복 쓰기 방지)

**인터페이스**:
- 트리거: EventBridge Cron (KR: 매일 16:30 KST, US: 매일 장 마감 후)
- 입력: 종목 목록 (환경변수 또는 DynamoDB 설정 테이블)
- 출력: DynamoDB 저장 결과

---

## Component 2: QuantAnalyzer

**목적**: 수집된 데이터를 기반으로 종목별 스코어를 산출하고 알람 후보를 식별

**책임**:
- `data_status = COMPLETE` 데이터만 참조 (Race Condition 방지)
- Global Kill-Switch 평가 (VIX, US10Y Yield 변동률, 환율 볼린저 밴드)
- Valuation Floor 계산 (PBR Min 기반)
- Momentum Pivot 감지 (MA20, RSI 30→35 돌파)
- 수급 분석 (한국 시장 한정: 외국인+기관 20거래일 누적 순매수합)
- 시장별 차등 스코어링 (KR: 40+30+30 / US: 60+40)
- 90점 이상 종목 AlertingEngine 호출
- DST 감지 및 시장 운영 시간 검증
- 멱등성 보장

**인터페이스**:
- 트리거: EventBridge (KR_Market_Hours / US_Market_Hours 별도 스케줄)
- 입력: DynamoDB StockDailyTable, StockStatsTable, MarketIndicatorTable
- 출력: 알람 후보 목록 → AlertingEngine 호출

---

## Component 3: AlertingEngine

**목적**: 고확신 알람 조건 충족 종목에 대해 Discord Webhook으로 메시지 발송

**책임**:
- 알람 메시지 포맷 생성 (현재가, 목표가, 손절가, 시그널 리스트, 스코어)
- Discord 2,000자 제한 검사 및 분할/요약 처리
- Discord Webhook 발송
- 발송 결과 로깅
- Secrets Manager에서 Webhook URL 로드 (전역 캐싱)

**인터페이스**:
- 트리거: QuantAnalyzer Lambda 직접 호출 (Invoke) 또는 EventBridge Event
- 입력: 알람 후보 종목 데이터 (스코어, 가격, 시그널)
- 출력: Discord 메시지 발송

---

## Component 4: Backtesting

**목적**: 과거 데이터로 알람 로직 검증 및 StockStatsTable Seed Data 생성

**책임**:
- 과거 특정 기간 데이터 로드 (yfinance 히스토리컬)
- 동일한 스코어링 로직 적용 (QuantAnalyzer 로직 재사용)
- 알람 발생 시점 및 이후 3~5개월 수익률 계산
- StockStatsTable 초기값(Seed Data) 생성 및 마이그레이션
- 결과 리포트 출력 (CSV 또는 콘솔)

**인터페이스**:
- 트리거: 수동 실행 (CLI)
- 입력: 종목 목록, 기간 파라미터 (start_date, end_date)
- 출력: 백테스팅 결과 리포트, StockStatsTable Seed Data

---

## Component 5: StatsUpdater (Weekly Batch)

**목적**: StockStatsTable의 역사적 통계값(PBR Min/Max/Median)을 주기적으로 갱신

**책임**:
- 최근 5~10년 PBR 데이터 재계산
- StockStatsTable 업데이트 (조건부 쓰기)
- 매주 토요일 자동 실행

**인터페이스**:
- 트리거: EventBridge Cron (매주 토요일 00:00 UTC)
- 입력: yfinance 히스토리컬 PBR
- 출력: StockStatsTable 업데이트
