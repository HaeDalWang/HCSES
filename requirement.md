Project: High-Confidence Stock Entry Scanner (HCSES)
[목표]
과거 데이터 기반의 저평가(Valuation Floor)와 기술적 반등(Momentum Pivot)이 합치되는 시점을 포착하여 한 달에 1~2회 고확신 알람을 송출함.

[기술 스택]

Language: Python 3.12

Infrastructure: AWS SAM (Lambda, DynamoDB, EventBridge, Secrets Manager)

Data Library: yfinance (가격/지표), FinanceDataReader (한국 시장 특화), pandas_datareader (Macro 데이터)

[핵심 컴포넌트 로직]

Data Collector (Daily Cron):

대상 종목의 OHLCV, PBR, PER, RSI 수집.

시장 지표(VIX, US10Y Yield, 원/달러 환율) 수집.

결과를 DynamoDB StockDailyTable에 저장.

Quant Analyzer (Daily 10x):

Valuation Floor: 최근 5~10년 PBR 데이터를 스캔하여 Min(PBR) 산출. 현재 PBR이 Min(PBR)×1.1 이하인지 체크.

Global Kill-Switch: * VIX>30 이면 즉시 중단.

10Y Yield 전일 대비 3% 급등 시 중단.

환율이 상단 볼린저 밴드 돌파 시 중단.

Momentum Pivot: Price>MA20 이면서 $RSI(14)$가 30 이하에서 35 위로 돌파 시 가점.

Alerting Engine:

위 조건의 가중치 합산 스코어가 90점 이상일 때만 Telegram API를 통해 메시지 전송.

메시지 포함 내용: 현재가, 목표가(PBR Median 기반), 손절가(PBR Min 기반), 감지된 시그널 리스트.

3. 지속적 운용을 위해 놓치고 있는 부분 (Operational Review)
구현 단계에서 반드시 고려해야 할 '운영의 묘'입니다.

① 데이터 품질 관리 (Data Integrity)
수정 주가(Adjusted Price): 배당, 액면분할 등이 반영되지 않은 주가 데이터를 사용하면 이평선과 수익률 계산이 모두 왜곡됩니다. 반드시 Adjusted Close를 사용하도록 로직을 강제해야 합니다.

API Rate Limiting: yfinance는 공식 API가 아니므로 단시간 대량 호출 시 IP 차단을 당합니다. 람다 실행 시 random.uniform(1, 3) 정도의 sleep을 주거나 호출 간격을 조정해야 합니다.

② 비용 최적화 (Cost Optimization)
DynamoDB에 매일 모든 종목의 전체 이력을 저장하면 비용이 선형적으로 증가합니다.

Raw Data: 최근 1년치만 유지 (TTL 설정).

Stats Data: 역사적 Min/Max PBR 등 계산된 통계값만 별도 테이블에 영구 보존.

③ 백테스팅 환경 (Validation)
에이전트에게 "지난 2022년 하락장에서도 이 알람이 울렸는지, 울렸다면 3~5개월 뒤 수익률이 어땠는지" 검증하는 스크립트를 먼저 짜게 하십시오. 이 과정 없이 실전에 투입하는 것은 위험합니다.

④ 예외 처리 (Error Handling)
금융 시장 휴장일(공휴일) 처리 로직이 누락되면 데이터가 None으로 들어와 분석 엔진이 크래시될 수 있습니다.

4. 시니어 엔지니어의 최종 조언
"손해 볼 수 없는 구간"을 찾는 핵심은 **'보수적 기준'**입니다. AI Agent에게 코딩을 시킬 때 **"조건이 하나라도 모호하면 True를 반환하지 말고 False를 반환하라"**는 원칙을 부여하십시오.
