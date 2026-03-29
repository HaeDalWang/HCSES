# Unit 4: Backtesting - Business Rules

## BR-01: 동일 스코어링 로직 재사용
- `shared/scoring.py`의 스코어링 함수를 그대로 사용 (코드 분기 없음)
- 백테스팅 결과와 실운영 결과의 일관성 보장

## BR-02: 히스토리컬 데이터 소스
- yfinance `auto_adjust=True` (Adjusted Close 강제)
- KR 종목 PBR 결측 시 FinanceDataReader 로컬 캐시 fallback (`~/.fdr_cache/`)
- 모든 수치 소수점 4자리 정규화

## BR-03: Kill-Switch 백테스팅 적용
- 과거 시점의 VIX, US10Y, KRW/USD 데이터로 Kill-Switch 평가
- Kill-Switch 활성 시점의 알람은 제외 (실운영과 동일 조건)

## BR-04: 수익률 계산 기간
- 알람 발생 후 60거래일(약 3개월), 90거래일, 150거래일(약 5개월) 수익률 계산
- `change_pct = (price_at_N - entry_price) / entry_price * 100`

## BR-05: Seed Data 생성
- 5~10년 PBR 히스토리컬 데이터로 Min/Max/Median 계산
- DynamoDB StockStatsTable에 업로드 (Unit 2 실행 전 필수)

## BR-06: 결과 리포트
- CSV 파일 출력: `backtest_results_YYYYMMDD.csv`
- 컬럼: ticker, market, signal_date, entry_price, score, return_60d_pct, return_90d_pct, return_150d_pct
- 콘솔 요약 출력 (총 알람 수, 평균 수익률)
