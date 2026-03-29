# HCSES — High-Confidence Stock Entry Scanner

과거 데이터 기반의 저평가(Valuation Floor)와 기술적 반등(Momentum Pivot)이 합치되는 시점을 포착하여
월 1~2회 고확신 Discord 알람을 송출하는 서버리스 퀀트 스캐닝 시스템.

## 아키텍처

```
EventBridge (Daily)
      │
      ▼
DataCollector (Lambda)
  ├─ yfinance / FinanceDataReader / pandas_datareader
  └─ DynamoDB (StockDailyTable, MarketIndicatorTable)
      │
EventBridge (장 중 10회)
      │
      ▼
QuantAnalyzer (Lambda)
  ├─ Kill-Switch (VIX, US10Y, KRW/USD)
  ├─ Valuation Floor / Momentum Pivot / Supply-Demand
  └─ Score ≥ 90 → AlertingEngine 호출
      │
      ▼
AlertingEngine (Lambda)
  └─ Discord Webhook 발송

EventBridge (매주 토요일)
      │
      ▼
StatsUpdater (Lambda)
  └─ PBR Min/Max/Median 재계산
```

## 주요 기능

- 한국(KOSPI/KOSDAQ) + 미국(NYSE/NASDAQ) 이중 시장 지원
- 시장별 차등 스코어링 (KR: 40+30+30 / US: 60+40)
- Global Kill-Switch (VIX, US10Y 급등, 환율 볼린저 돌파)
- stale 지표 감지 시 보수적 임계값 자동 강화
- 백테스팅 스크립트 (과거 알람 검증 + 수익률 계산)
- Seed Data 마이그레이션 (StockStatsTable 초기값)

## 기술 스택

| 항목 | 선택 |
|---|---|
| Language | Python 3.12 |
| Infra | AWS SAM (Lambda, DynamoDB, EventBridge, Secrets Manager) |
| Data | yfinance, FinanceDataReader, pandas_datareader (FRED) |
| Alert | Discord Webhook |
| Region | ap-northeast-2 (서울) |

## 프로젝트 구조

```
hcses/
├── src/
│   ├── data_collector/      # Unit 1: 일별 데이터 수집
│   ├── quant_analyzer/      # Unit 2: 스코어링 엔진
│   ├── alerting_engine/     # Unit 3: Discord 알람
│   ├── stats_updater/       # Unit 1 부속: 주간 PBR 통계
│   ├── backtesting/         # Unit 4: 백테스팅 CLI
│   └── shared/              # 공유 모듈
├── tests/unit/              # 단위 테스트
├── template.yaml            # AWS SAM
├── requirements.txt
└── user-guide.md            # 배포 및 테스트 가이드
```

## 퀵스타트

[user-guide.md](user-guide.md) 참조 — 사전 준비부터 배포, 수동 Invoke 테스트, CloudWatch 확인까지 Step-by-Step 가이드.

## 설계 원칙

- 조건이 하나라도 모호하면 True가 아닌 False를 반환 (보수적 원칙)
- 모든 외부 호출에 명시적 예외 처리 + 재시도
- 종목별 실패 격리 (Bulkhead 패턴)
- 멱등성 보장 (DynamoDB ConditionExpression)
- 절대값(`_value`) vs 변동률(`_pct`) 변수명 규칙 (EC-02)

## 라이선스

Private — 비공개 프로젝트
