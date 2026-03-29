# Unit 1: DataCollector - Business Rules

## BR-01: Adjusted Close 강제 사용
- OHLCV 수집 시 반드시 수정 주가(Adjusted Close) 사용
- yfinance: `auto_adjust=True` 파라미터 강제
- 미지원 소스 사용 금지

## BR-02: 수치 정규화
- 모든 float 수치는 `round(x, 4)` 적용 후 저장
- None/NaN은 그대로 유지 (0으로 대체 금지)

## BR-03: KR PBR 결측 처리 (EC-01)
- yfinance KR PBR 결측(None/NaN) 시:
  1. FinanceDataReader PBR 시도
  2. 모두 실패 시 `pbr_value = None` 저장
- 결측 발생 시 CloudWatch WARNING 로그 기록
- 크래시 금지 — 나머지 필드는 정상 저장

## BR-04: Rate Limiting
- 종목 간 `time.sleep(random.uniform(1, 3))` 적용
- yfinance 연속 호출 방지

## BR-05: 공휴일/휴장일 처리
- `is_market_holiday(market, date)` 반환 True 시 해당 종목 skip
- 데이터 없음(빈 DataFrame) 반환 시도 graceful skip
- 휴장일 skip은 정상 동작 (오류 아님)

## BR-06: data_status 전환 규칙
- 수집 시작: `data_status = COLLECTING`
- 모든 필드 수집 완료: `data_status = COMPLETE`
- 수집 중 예외 발생: `data_status = FAILED`
- FAILED 레코드는 다음 실행 시 재시도 가능

## BR-07: 멱등성 (TC-01)
- DynamoDB PutItem 시 `ConditionExpression: attribute_not_exists(ticker) AND attribute_not_exists(#date)`
- 이미 COMPLETE 레코드 존재 시 덮어쓰기 금지
- FAILED 레코드는 재시도 허용 (UpdateItem 사용)

## BR-08: 외국인/기관 순매수 (KR only)
- FinanceDataReader로 당일 외국인 순매수, 기관 순매수 수집
- 데이터 미제공 시 `None` 저장 (0 대체 금지 — EC-02 원칙)

## BR-09: 시장 지표 수집
- VIX: yfinance `^VIX`
- US10Y: pandas_datareader FRED `DGS10`
- KRW/USD: yfinance `KRW=X`
- 볼린저 밴드(KRW/USD): 20일 이동평균 ± 2σ 계산
- 전일 대비 변동률: `change_pct = (today - prev) / prev * 100`
