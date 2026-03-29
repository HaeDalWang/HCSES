# HCSES - Component Methods

## DataCollector

```python
# 진입점
def handler(event: dict, context: object) -> dict
    # Lambda 핸들러. EventBridge 트리거.

def load_ticker_list(market: str) -> list[str]
    # 종목 목록 로드. market: 'KR' | 'US'
    # 반환: 티커 리스트

def collect_stock_data(ticker: str, market: str) -> StockDailyRecord | None
    # 단일 종목 OHLCV + PBR + PER + RSI 수집
    # Adjusted Close 강제 사용
    # 휴장일/결측 시 None 반환 (graceful skip)

def collect_kr_supply_demand(ticker: str) -> SupplyDemandRecord | None
    # 한국 시장 전용: 외국인+기관 20거래일 누적 순매수합 수집
    # FinanceDataReader 사용

def collect_market_indicators() -> MarketIndicatorRecord | None
    # VIX, US10Y Yield, KRW/USD 환율 수집
    # pandas_datareader (FRED) + yfinance

def normalize_numeric_fields(record: StockDailyRecord) -> StockDailyRecord
    # 모든 수치 필드를 소수점 4자리로 반올림 (round(x, 4))
    # yfinance / FinanceDataReader 간 정밀도 차이 정규화
    # None/NaN 필드는 그대로 유지

def save_stock_daily(record: StockDailyRecord) -> bool
    # DynamoDB StockDailyTable 저장
    # data_status: COLLECTING → COMPLETE
    # 멱등성: ConditionExpression으로 중복 방지

def save_market_indicator(record: MarketIndicatorRecord) -> bool
    # DynamoDB MarketIndicatorTable 저장

def is_market_holiday(market: str, date: date) -> bool
    # 공휴일/휴장일 여부 확인
```

---

## QuantAnalyzer

```python
def handler(event: dict, context: object) -> dict
    # Lambda 핸들러. EventBridge 트리거 (KR/US 별도).

def detect_dst_offset(market: str, dt: datetime) -> int
    # 미국 시장 DST 적용 여부 감지
    # 반환: UTC offset (시간 단위, -4 또는 -5)
    # pytz 또는 zoneinfo 사용

def is_within_market_hours(market: str, dt: datetime) -> bool
    # 현재 시각이 해당 시장 운영 시간 내인지 확인
    # DST 반영

def get_latest_complete_data(ticker: str, market: str) -> StockDailyRecord | None
    # data_status = 'COMPLETE' AND analysis_status != 'DONE'인 최신 레코드 조회
    # 이미 분석 완료된 레코드는 skip (장 중 재계산 방지)
    # 없으면 None 반환

def mark_analysis_done(ticker: str, date: date) -> None
    # 분석 완료 후 StockDailyTable의 analysis_status = 'DONE' 업데이트

def evaluate_global_kill_switch(indicators: MarketIndicatorRecord) -> KillSwitchResult
    # VIX > 30 체크
    # US10Y Yield 전일 대비 change_pct > 3% 체크
    # KRW/USD 상단 볼린저 밴드 돌파 체크
    # 하나라도 활성화 시 score_value = 0 강제

def calculate_valuation_floor_score(ticker: str, pbr_value: float, market: str) -> float
    # PBR Min 조회 (StockStatsTable)
    # 조건: pbr_value <= pbr_min_value * 1.1
    # KR: 40점, US: 60점 반환 (미충족 시 0점)
    # PBR 결측 시 0점 반환 (EC-01 적용)

def calculate_momentum_pivot_score(
    price_value: float, ma20_value: float,
    rsi_prev_level: float, rsi_curr_level: float,
    market: str
) -> float
    # Price > MA20 AND RSI 30→35 돌파 체크
    # KR: 30점, US: 40점 반환

def calculate_supply_demand_score(ticker: str) -> float
    # 한국 시장 전용
    # 외국인+기관 20거래일 누적 순매수합 > 0 전환 체크
    # 30점 반환 (미충족 또는 US 시장 시 0점)

def calculate_total_score(
    valuation_score: float,
    momentum_score: float,
    supply_demand_score: float,
    kill_switch: KillSwitchResult
) -> float
    # 가중치 합산
    # kill_switch 활성화 시 0.0 강제 반환

def run_analysis(ticker: str, market: str) -> AnalysisResult
    # 단일 종목 전체 분석 파이프라인 실행
    # 조건 모호 시 False 반환 (보수적 원칙)
```

---

## AlertingEngine

```python
def handler(event: dict, context: object) -> dict
    # Lambda 핸들러.

def get_discord_webhook_url() -> str
    # Secrets Manager에서 URL 로드
    # 전역 변수 캐싱 (Lambda 컨텍스트 재사용 시 API 재호출 금지)

def calculate_target_price(ticker: str, current_price_value: float) -> float
    # 목표가: PBR Median 기반 계산
    # StockStatsTable에서 pbr_median_value 조회

def calculate_stop_loss_price(ticker: str, current_price_value: float) -> float
    # 손절가: PBR Min 기반 계산

def format_alert_message(result: AnalysisResult) -> str
    # 알람 메시지 포맷 생성
    # 포함: 종목명, 티커, 현재가, 목표가, 손절가, 시그널 리스트, 스코어

def truncate_message_if_needed(message: str, limit: int = 2000) -> str
    # Discord 2,000자 제한 초과 시 요약 처리
    # 초과 여부 로깅

def send_discord_alert(message: str) -> bool
    # Discord Webhook POST 요청
    # 실패 시 최대 3회 재시도
```

---

## Backtesting

```python
def run_backtest(
    tickers: list[str],
    start_date: date,
    end_date: date,
    market: str
) -> BacktestReport
    # 전체 백테스팅 실행 파이프라인

def load_historical_data(ticker: str, start_date: date, end_date: date) -> pd.DataFrame
    # yfinance 히스토리컬 데이터 로드 (Adjusted Close)
    # KR 종목 PBR 결측 시 FinanceDataReader 로컬 DB 캐싱으로 fallback
    # FDR 캐시 경로: ~/.fdr_cache/ (Unit 4 전용)

def simulate_scoring(df: pd.DataFrame, market: str) -> list[AlertSignal]
    # QuantAnalyzer 스코어링 로직 재사용
    # 알람 발생 시점 목록 반환

def calculate_forward_returns(
    df: pd.DataFrame,
    signal_date: date,
    periods: list[int]  # [60, 90, 150] 거래일
) -> dict[int, float]
    # 알람 발생 후 N거래일 수익률 계산 (change_pct)

def generate_seed_data(tickers: list[str]) -> list[StockStatsRecord]
    # StockStatsTable 초기값 생성
    # 5~10년 PBR Min/Max/Median 계산

def migrate_seed_data(records: list[StockStatsRecord]) -> None
    # DynamoDB StockStatsTable에 Seed Data 업로드

def export_report(report: BacktestReport, output_path: str) -> None
    # 결과 CSV 또는 콘솔 출력
```

---

## StatsUpdater

```python
def handler(event: dict, context: object) -> dict
    # Lambda 핸들러. 매주 토요일 EventBridge 트리거.

def recalculate_pbr_stats(ticker: str) -> StockStatsRecord
    # 최근 5~10년 PBR 재계산
    # pbr_min_value, pbr_max_value, pbr_median_value 산출

def update_stats_table(record: StockStatsRecord) -> bool
    # StockStatsTable 조건부 업데이트
    # 멱등성 보장
```
