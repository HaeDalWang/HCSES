# HCSES — High-Confidence Stock Entry Scanner

> "언제 볼 것인가"를 알려주는 서버리스 퀀트 스캐닝 시스템

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![AWS SAM](https://img.shields.io/badge/AWS_SAM-Serverless-FF9900?logo=amazonaws&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-NoSQL-4053D6?logo=amazondynamodb&logoColor=white)
![Discord](https://img.shields.io/badge/Alert-Discord_Webhook-5865F2?logo=discord&logoColor=white)
![Cost](https://img.shields.io/badge/월_비용-~%242.47-green)
![License](https://img.shields.io/badge/License-Private-red)

**과거 데이터 기반의 저평가(Valuation Floor)** 와 **기술적 반등(Momentum Pivot)** 이 동시에 충족되는 순간을 포착하여 Discord로 고확신 알림을 송출합니다. 월 $2.47, 완전 서버리스, 노이즈 없는 신호만.

---

## 왜 만들었나

주식/경제 지식 없이도 **"지금 이 종목을 봐야 할 이유"** 를 데이터로 판단받고 싶었습니다.

- 매일 차트를 볼 시간도, 재무제표를 읽을 지식도 없음
- 그렇다고 감으로 매수하고 싶지 않음
- 확률만 높이면 됨 — 조건이 충족됐을 때만 알림, 나머지는 무시

결과적으로 **"조건이 모두 충족됐을 때만 True"** 라는 보수적 원칙 하에 만든 자동화 스캐너입니다.

---

## 핵심 설계 원칙

| 원칙 | 내용 |
|------|------|
| 보수적 판단 | 조건 하나라도 모호하면 False 반환 |
| 격리 | 종목별 실패가 전체에 영향 없음 (Bulkhead 패턴) |
| 멱등성 | 중복 실행해도 결과 동일 (DynamoDB ConditionExpression) |
| 명확성 | 절대값(`_value`) vs 변동률(`_pct`) 변수명 규칙 엄수 |
| 복구 탄력성 | 모든 외부 호출에 명시적 예외 처리 + 지수 백오프 재시도 |

---

## 스코어링 로직

알림은 **score >= 90** 일 때만 발송됩니다.

### US 시장 (60 + 40)

```
Valuation Floor  60점  current_PBR <= pbr_min × 1.1
Momentum Pivot   40점  Price > MA20
                       AND RSI_prev <= 30
                       AND RSI_curr  > 35
```

### KR 시장 (40 + 30 + 30)

```
Valuation Floor  40점  current_PBR <= pbr_min × 1.1  (2010년 이후 데이터 기준)
Momentum Pivot   30점  Price > MA20
                       AND RSI_prev <= 30
                       AND RSI_curr  > 35
Supply-Demand    30점  외인 + 기관 순매수 누적 20일 음→양 전환
```

### Global Kill-Switch

```
VIX > 30          → 전 종목 score 강제 0 (알림 차단)
25 < VIX <= 30    → score 유지 + ⚠️ 경고 문구 추가
US10Y 변동률 > 3% → 전 종목 score 강제 0
```

> **설계 의도:** VIX 25~30 구간(지정학적 불안 등)에서 PBR 저점 신호가 오히려 자주 발생합니다. 이 구간을 완전 차단하면 가장 좋은 신호를 놓칩니다. 경고 문구만 추가한 채 신호는 유지합니다.

---

## Discord 알림 포맷

```
🚨 매수 신호 | Micron Technology (MU) | NASDAQ

━━━━━━━━ 진입 근거 ━━━━━━━━
현재가:         $98.45
HCSES 점수:     92 / 100
  └ Valuation:  60 (PBR Floor 충족)
  └ Momentum:   32 (RSI 28→37 돌파)

PBR 현재:       1.82x
PBR 역사 최저:  1.71x
PBR 중앙값:     3.10x

━━━━━━━━ 얼마나 살까 ━━━━━━━━
ATR(14):        $4.20
종목당 한도:    총 예산의 10%

━━━━━━━━ 출구 전략 ━━━━━━━━
손절가:  $90.05  (현재가 - 2×ATR)   → -8.5%
1차익절: $119.00 (목표가의 70%)     → +20.9%
목표가:  $167.80 (PBR 중앙값 기준)  → +70.4%
타임컷:  매수일로부터 60일 내 미달성 시 전량 매도

━━━━━━━━ 시장 상태 ━━━━━━━━
VIX:     18.3 (정상)
US10Y:   4.21% (정상)
신호일:  2026-04-02 14:30 ET
```

---

## 아키텍처

```
EventBridge (Daily)
      │
      ▼
DataCollector (Lambda)
  ├─ yfinance / FinanceDataReader / pandas_datareader (FRED)
  └─ DynamoDB (StockDailyTable, MarketIndicatorTable)
      │
EventBridge (장 중 10회)
      │
      ▼
QuantAnalyzer (Lambda)
  ├─ Global Kill-Switch (VIX, US10Y)
  ├─ Valuation Floor + Momentum Pivot + Supply-Demand (KR)
  └─ Score >= 90 → AlertingEngine 호출
      │
      ▼
AlertingEngine (Lambda)
  └─ Discord Webhook 발송

EventBridge (매주 토요일)
      │
      ▼
StatsUpdater (Lambda)
  └─ PBR Min / Max / Median 주간 재계산
```

---

## 운영 종목 (36개)

```python
TICKER_LIST = {
    "KR": [
        "005930.KS",  # 삼성전자
        "000660.KS",  # SK하이닉스
        "035420.KS",  # NAVER
        "005380.KS",  # 현대차
        "000270.KS",  # 기아
        "105560.KS",  # KB금융
        "010950.KS",  # S-Oil
        "329180.KS",  # HD현대중공업
        "005490.KS",  # POSCO홀딩스
        "033780.KS",  # KT&G
        "030200.KS",  # KT
    ],
    "US": [
        # 반도체/장비
        "MU", "AMD", "INTC", "QCOM", "AMAT", "LRCX",
        # 빅테크
        "META",
        # 금융
        "JPM", "GS", "C", "WFC", "BAC",
        # 에너지
        "XOM", "CVX", "OXY", "DVN",
        # 소재/철강
        "FCX", "NUE",
        # 자동차/산업재
        "F", "GM", "GE", "CAT",
        # 헬스케어
        "UNH", "BMY",
        # 통신
        "T",
    ]
}
```

**종목 선정 기준:** PBR 역사적 변동폭이 큰 사이클주 위주. 방어주/빅테크는 PBR이 역사적 저점에 오는 경우가 극히 드물어 이 시스템과 궁합이 맞지 않습니다. 종목 추가/제거 기준은 [TICKERS.md](./TICKERS.md) 참조.

---

## 기술 스택

| 항목 | 선택 |
|------|------|
| Language | Python 3.12 |
| Infra | AWS SAM (Lambda, DynamoDB, EventBridge, Secrets Manager) |
| Data | yfinance, FinanceDataReader, pandas_datareader (FRED) |
| Alert | Discord Webhook |
| Region | ap-northeast-2 (서울) |

---

## 프로젝트 구조

```
hcses/
├── src/
│   ├── data_collector/      # Unit 1: 일별 데이터 수집
│   ├── quant_analyzer/      # Unit 2: 스코어링 엔진
│   ├── alerting_engine/     # Unit 3: Discord 알림
│   ├── stats_updater/       # 주간 PBR 통계 재계산
│   ├── backtesting/         # Unit 4: 백테스팅 CLI
│   └── shared/              # 공유 모듈
├── tests/unit/              # 단위 테스트
├── template.yaml            # AWS SAM
├── TECHNICAL.md             # 기술 상세 설계 문서
├── TICKERS.md               # 운영 종목 목록 및 편입 사유
├── requirements.txt
└── user-guide.md            # 배포 Step-by-Step 가이드
```

---

## 예상 월간 AWS 비용

> ap-northeast-2 기준, 프리티어 미적용, 36종목 운영 시

| 서비스 | 산출 근거 | 월 예상 비용 |
|--------|-----------|-------------|
| Lambda (DataCollector KR/US) | 2회/일 × 22일 × 512MB × 480초 | $0.60 |
| Lambda (QuantAnalyzer KR/US) | 20회/일 × 22일 × 256MB × 180초 | $0.85 |
| Lambda (AlertingEngine) | ~2회/월 × 128MB × 5초 | $0.00 |
| Lambda (StatsUpdater) | 4회/월 × 256MB × 300초 | $0.01 |
| DynamoDB (읽기/쓰기/스토리지) | ~2,500 WCU + ~40,000 RCU + 0.5GB | $0.18 |
| EventBridge | ~500 이벤트/월 (무료 한도 내) | $0.00 |
| Secrets Manager | 1 시크릿 × $0.40 | $0.40 |
| CloudWatch Logs | 수집 ~400MB + 보관 ~1.2GB (90일) | $0.43 |
| **합계** | | **~$2.47/월** |

> 종목 수 증가 시 Lambda 실행 시간과 DynamoDB I/O가 선형 증가합니다.
> 100종목 기준 약 $4~5/월, 200종목 기준 약 $8~10/월로 추정됩니다.

---

## 퀵스타트

[user-guide.md](./user-guide.md) 참조 — 사전 준비부터 배포, Seed Data 마이그레이션, 수동 테스트, CloudWatch 확인까지 Step-by-Step.

기술적 원리는 [TECHNICAL.md](./TECHNICAL.md) 참조.

---

## 알려진 한계

- yfinance 단일 의존 — 장애 시 수집 불가 → V2에서 fallback 소스 추가 예정
- PBR은 최근 분기 재무제표 기준 단일값 (과거 BPS 변동 미반영)
- KR 수급 데이터는 전일 마감 기준 (장 중 실시간 아님)

---

## License

Private — 비공개 프로젝트
