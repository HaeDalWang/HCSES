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

### Tier 2: 단기 스윙 (score >= 70 시 알림)

```
기술적 반등    40점  RSI_prev <= 35 AND RSI_curr > 35
                    OR RSI 2일 연속 상승 (< 40 구간)
가격 지지      30점  볼린저 하단(20, 2σ) 터치 후 반등
                    OR MA5 돌파 + MA20 미달
거래량 확인    30점  Volume > 20일 평균 × 1.5
                    OR 외인+기관 동시 순매수 (KR)
```

**출구 전략:** 목표가 = min(MA20, +10%), 손절가 = ATR×1.5, 타임컷 = 15거래일

상세 설계: [docs/TIER2-SWING-DESIGN.md](./docs/TIER2-SWING-DESIGN.md)

### Global Kill-Switch

```
VIX > 30          → Tier 1 & 2 전면 차단
25 < VIX <= 30    → Tier 1: 경고 문구만 / Tier 2: score × 0.7 패널티
US10Y 변동률 > 3% → 전면 차단
KRWUSD > BB upper → 전면 차단
```

> **설계 의도:** VIX 25~30 구간에서 Tier 1은 장기 진입이라 기회이지만, Tier 2는 단기 반등 신뢰도가 떨어지므로 30% 할인합니다.

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

### Tier 2 알림 포맷 (별도 채널)

```
⚡ 단기 기회 | NVIDIA (NVDA) | US

━━━━━━━━ 진입 근거 ━━━━━━━━
현재가:         $105.20
Swing Score:    100 / 100
  └ 기술반등:   40 (RSI 33→38 탈출)
  └ 가격지지:   30 (볼린저 하단 반등)
  └ 거래량:     30 (2.1x 서프라이즈)

━━━━━━━━ 출구 전략 ━━━━━━━━
목표가:  $110.00  (min(MA20, +10%))  → +4.6%
손절가:  $97.00   (현재가 - 1.5×ATR) → -7.8%
타임컷:  15거래일

⚠️ 단기 스윙 목적 — 목표가 도달 시 즉시 청산 권장
```

---

## 아키텍처

```
EventBridge (Daily)
      │
      ▼
DataCollector (Lambda)
  ├─ yfinance / FinanceDataReader (KR 수급)
  └─ DynamoDB (StockDailyTable, MarketIndicatorTable)
      │
      ├────────────────────────────────────────┐
      │                                        │
EventBridge (장 중 10회)              EventBridge (장 중 3회)
      │                                        │
      ▼                                        ▼
QuantAnalyzer (Lambda)               SwingAnalyzer (Lambda)
  ├─ Global Kill-Switch                ├─ Kill-Switch (공유)
  ├─ Valuation + Momentum             ├─ 기술반등 + 가격지지 + 거래량
  │   + Supply-Demand (KR)             ├─ VIX 25~30 패널티 (×0.7)
  └─ Score >= 90 → 🚨 Tier 1          └─ Score >= 70 → ⚡ Tier 2
      │                                        │
      ▼                                        ▼
AlertingEngine (Lambda) ◄──────────────────────┘
  ├─ Tier 1 → Discord #hcses-alert (고확신 진입)
  └─ Tier 2 → Discord #hcses-swing (단기 기회)

EventBridge (매주 토요일)
      │
      ▼
StatsUpdater (Lambda)
  └─ PBR Min / Max / Median 주간 재계산
```

---

## 운영 종목 (총 61개)

### Tier 1 전용 (11 KR + 25 US = 36개)

PBR 역사적 변동폭이 큰 사이클주·가치주 위주. [TICKERS.md](./TICKERS.md) 참조.

### Tier 2 전용 (10 KR + 15 US = 25개, 일부 Tier 1과 중복)

고변동·고유동성 종목. 기술적 과매도 후 빠른 반등이 빈번한 종목 위주.

```python
# Tier 2 전용 종목 (기존 Tier 1 외 추가분)
SWING_TICKERS = {
    "KR": ["373220.KS", "006400.KS", "035720.KS", "247540.KS", "086520.KS",
           "003670.KS", "042700.KS", "012330.KS", "034730.KS", "028260.KS"],
    "US": ["NVDA", "TSLA", "SOFI", "COIN", "ROKU", "SNAP", "RIVN", "MARA",
           "PLTR", "SQ", "DKNG", "SMCI", "CRWD", "NET", "ARM"],
}
```

종목 선정 기준: [TICKERS.md](./TICKERS.md) 참조.

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
│   ├── quant_analyzer/      # Unit 2: Tier 1 스코어링 엔진
│   ├── swing_analyzer/      # Unit 5: Tier 2 단기 스윙 분석
│   ├── alerting_engine/     # Unit 3: Discord 알림 (Tier 1 & 2 공용)
│   ├── stats_updater/       # 주간 PBR 통계 재계산
│   ├── backtesting/         # Unit 4: 백테스팅 CLI
│   └── shared/              # 공유 모듈
├── tests/unit/              # 단위 테스트
├── scripts/                 # 운영 스크립트 (백필 등)
├── docs/                    # 상세 설계 문서
│   └── TIER2-SWING-DESIGN.md
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
| Lambda (SwingAnalyzer KR/US) | 6회/일 × 22일 × 256MB × 180초 | $0.40 |
| Lambda (AlertingEngine) | ~5회/월 × 128MB × 5초 | $0.00 |
| Lambda (StatsUpdater) | 4회/월 × 256MB × 300초 | $0.01 |
| DynamoDB (읽기/쓰기/스토리지) | ~2,500 WCU + ~40,000 RCU + 0.5GB | $0.18 |
| EventBridge | ~500 이벤트/월 (무료 한도 내) | $0.00 |
| Secrets Manager | 1 시크릿 × $0.40 | $0.40 |
| CloudWatch Logs | 수집 ~400MB + 보관 ~1.2GB (90일) | $0.43 |
| DynamoDB (SwingCooldown) | 미미 | $0.01 |
| **합계** | | **~$2.90/월** |

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
