# 모니터링 대상 종목 (Tickers)

본 시스템은 2계층(Tier)으로 운영됩니다:

- **Tier 1** (36종목): Valuation Floor + Momentum Pivot — PBR 역사적 저점 + 기술적 반등 동시 충족 시 고확신 진입 알림
- **Tier 2** (25종목): Short-Swing — 기술적 과매도 후 단기 반등 기회 포착 (일부 Tier 1과 중복)

---

# Tier 1: 고확신 진입 종목 (36개)

Valuation Floor(역사적 PBR 하단) 및 Momentum Pivot 로직과의 수학적 정합성이 검증된 종목입니다.
오탐(False Positive)과 중복 알람을 방지하기 위해 종목 간 상관관계를 배제하고 사이클 및 가치주 중심으로 최적화했습니다.

---

## 한국 시장 (KR) — 11종목

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| 005930.KS | 삼성전자 | 반도체 사이클 (PBR 밴드 플레이의 표준) |
| 000660.KS | SK하이닉스 | 반도체 사이클 (주가 변동성 극대화 타겟) |
| 035420.KS | NAVER | 낙폭 과대 플랫폼 (성장 프리미엄 소멸 후 PBR 하단 진입) |
| 005380.KS | 현대차 | 우량 가치주 및 수출 주도 경기민감주 |
| 000270.KS | 기아 | 우량 가치주 및 수출 주도 경기민감주 |
| 105560.KS | KB금융 | 금융 대표주 (강력한 PBR 하방 경직성, 중복 알람 방지용 단독 편성) |
| 010950.KS | S-Oil | 정유 사이클 대표주 |
| 329180.KS | HD현대중공업 | 조선업 사이클 대표주 |
| 005490.KS | POSCO홀딩스 | 철강/소재 사이클 (분할 이슈에 따른 BPS 왜곡이 없는 우량주) |
| 033780.KS | KT&G | 경기 방어 및 전통 배당주 |
| 030200.KS | KT | 통신 방어주 (극단적 하방 경직성 확보) |

> KR 종목 pbr_min_value는 2010-01-01 이후 데이터 기준으로 계산됩니다.
> IMF(1997), 금융위기(2008) 극단값을 제외하여 현실적인 임계값을 유지합니다.

---

## 미국 시장 (US) — 25종목

### 반도체 / 장비 (6종목)

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| MU | Micron Technology | 메모리 반도체 사이클 (PBR 저점 반등 패턴 극명) |
| AMD | Advanced Micro Devices | 비메모리 반도체 사이클 |
| INTC | Intel | 파운드리 전환 구조조정 중 (PBR 저점 진입 이력 검증, 고변동성) |
| QCOM | Qualcomm | 모바일 칩셋 사이클 (스마트폰 업황 연동, MU·AMD와 독립 사이클) |
| AMAT | Applied Materials | 반도체 장비 사이클 (꾸준한 BPS 증가) |
| LRCX | Lam Research | 식각 장비 사이클 (AMAT과 다른 세부 장비 사이클 확보) |

### 빅테크 (1종목)

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| META | Meta Platforms | 빅테크 중 유일 편입 (과거 실적 쇼크 시 PBR 하단 터치 이력 검증) |

### 금융 (5종목)

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| JPM | JPMorgan Chase | 상업 은행 대표주 (안정적인 자산 가치) |
| GS | Goldman Sachs | 투자 은행 (JPM과 동조화되지 않는 별도의 IB 사이클) |
| C | Citigroup | 글로벌 IB (구조조정 후 PBR 0.3대 저점 반등 패턴) |
| WFC | Wells Fargo | 소매 은행 (규제 리스크 해소 시 PBR 급등 이력) |
| BAC | Bank of America | 소매 금융 (금리 사이클 민감, 분산 확보) |

### 에너지 (4종목)

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| XOM | ExxonMobil | 에너지 메이저 (안정적 BPS, 사이클 대표주) |
| CVX | Chevron | 에너지 메이저 (XOM과 독립적 배당/자산 구조) |
| OXY | Occidental Petroleum | 에너지 E&P (고변동성, PBR 1.0 이하 진입 이력) |
| DVN | Devon Energy | 셰일 E&P (유가 사이클 직결, 변동성 극대화 타겟) |

### 소재 / 철강 (2종목)

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| FCX | Freeport-McMoRan | 구리 채굴 대표주 (원자재 사이클, PBR 저점 반등 패턴 검증) |
| NUE | Nucor | 미국 전기로 철강 (건설 경기 사이클 연동, 안정적 BPS) |

### 자동차 / 산업재 (4종목)

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| F | Ford | EV 전환 비용 과다 반영 시 PBR 저점 진입 패턴 |
| GM | General Motors | F와 독립적인 사이클 (GM 크루즈 리스크 해소 후 PBR 반등) |
| GE | GE Aerospace | 분사 이후 고마진 항공 엔진 순수회사 (PBR 재평가 구간) |
| CAT | Caterpillar | 건설/광산 장비 (글로벌 인프라 사이클 연동) |

### 헬스케어 (2종목)

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| UNH | UnitedHealth Group | 헬스케어 방어주 (적절한 주가 변동성 확보) |
| BMY | Bristol-Myers Squibb | 빅파마 (파이프라인 리스크 과반영 구간 PBR 저점 진입) |

### 통신 (1종목)

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| T | AT&T | 통신 방어주 (부채 감소 진행 중, 배당 안정성 회복 구간) |

---

---

# Tier 2: 단기 스윙 종목 (25개)

선정 기준: 베타 > 1.3, 일평균 거래량 풍부, ATR/Close > 2.5%, 평균회귀 경향 강한 종목.

## 한국 시장 (KR) — 15종목

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| 005930.KS | 삼성전자 | (Tier 1 겸용) 유동성 최고, 지지선 반등 명확 |
| 000660.KS | SK하이닉스 | (Tier 1 겸용) 반도체 사이클, 단기 반등 빈번 |
| 035420.KS | NAVER | (Tier 1 겸용) 기술주 센티먼트, 기관 매수 패턴 |
| 005380.KS | 현대차 | (Tier 1 겸용) 자동차 사이클, 외인 매매 패턴 명확 |
| 000270.KS | 기아 | (Tier 1 겸용) 위와 동일 |
| 373220.KS | LG에너지솔루션 | 베타 높음, 배터리 센티먼트 급변 |
| 006400.KS | 삼성SDI | 2차전지, 과매도 시 외인 저가매수 패턴 |
| 035720.KS | 카카오 | 고베타, 센티먼트 드리븐, RSI 35 이하 빈번 |
| 247540.KS | 에코프로비엠 | 극단적 변동성, 단기 반등 폭 큼 |
| 086520.KS | 에코프로 | 위와 동일 섹터, 테마 동조 |
| 003670.KS | 포스코퓨처엠 | 2차전지 소재, 사이클 급변 |
| 042700.KS | 한미반도체 | AI 테마, 고변동성 |
| 012330.KS | 현대모비스 | 자동차 부품, 기술적 지지 반등 |
| 034730.KS | SK | 지주 할인 축소/확대 반복 |
| 028260.KS | 삼성물산 | 지배구조 이벤트 + 기술적 지지 반등 |

## 미국 시장 (US) — 20종목

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| NVDA | NVIDIA | 베타 ~1.7, 거래량 폭발적, 과매도 시 반등 빠름 |
| TSLA | Tesla | 베타 ~2.0, 변동성 최상위, 단기 반등 패턴 빈번 |
| AMD | Advanced Micro Devices | (Tier 1 겸용) 베타 ~1.6, 스윙 트레이더 선호 |
| MU | Micron Technology | (Tier 1 겸용) 사이클 극심, RSI 35 이하 빈번 |
| SOFI | SoFi Technologies | 베타 ~1.8, 높은 변동성, 유동성 풍부 |
| COIN | Coinbase | 베타 ~2.5, 극단적 과매도→반등 패턴 |
| ROKU | Roku | 베타 ~1.8, 실적 시즌 급락→반등 빈번 |
| SNAP | Snap | 베타 ~1.5, 센티먼트 급변, 기술적 반등 뚜렷 |
| RIVN | Rivian | 베타 ~2.0, 고변동 성장주 |
| MARA | Marathon Digital | 베타 ~3.0, 극단적 변동 (리스크 높음) |
| PLTR | Palantir | 베타 ~1.6, 모멘텀 급변, 단기 반등 강함 |
| SQ | Block | 베타 ~1.7, 과매도→반등 패턴 선명 |
| DKNG | DraftKings | 베타 ~1.6, 센티먼트 드리븐 |
| FCX | Freeport-McMoRan | (Tier 1 겸용) 원자재 사이클, 단기 반등 빈번 |
| XOM | ExxonMobil | (Tier 1 겸용) 유가 급변 시 과매도 진입 |
| BAC | Bank of America | (Tier 1 겸용) 금리 이벤트 시 급락→반등 |
| SMCI | Super Micro Computer | 베타 ~2.5, 급등락 심함, 유동성 좋음 |
| CRWD | CrowdStrike | 베타 ~1.4, 이벤트 드리븐 급락→회복 |
| NET | Cloudflare | 베타 ~1.5, 성장주 센티먼트 반영 빠름 |
| ARM | ARM Holdings | 베타 ~1.8, IPO 이후 변동성 큼 |

> **Tier 2 부적합 (Tier 1 전용):** T, UNH, KT&G, KT, S-Oil — 변동성 너무 낮아 15일 내 +10% 비현실적

---

## 종목 추가 방법

### Tier 1 종목 추가

`src/data_collector/handler.py`의 `TICKER_LIST`와 `TICKER_NAMES`에 동시 추가 후,
신규 종목 Seed Data 생성 필수:

```bash
# KR 신규 종목 (2010-01-01 기준 자동 적용)
PYTHONPATH=. python -m src.backtesting.backtest_runner \
  --tickers [NEW_KR_TICKER] \
  --market KR \
  --start 2010-01-01 --end $(date +%Y-%m-%d) --seed

# US 신규 종목
PYTHONPATH=. python -m src.backtesting.backtest_runner \
  --tickers [NEW_US_TICKER] \
  --market US \
  --start 2017-01-01 --end $(date +%Y-%m-%d) --seed
```

이후 `sam build --use-container && sam deploy` 재배포.

### Tier 2 종목 추가

1. `src/swing_analyzer/tickers.py`의 `SWING_TICKER_LIST`와 `SWING_TICKER_NAMES`에 추가
2. `src/data_collector/handler.py`의 `TICKER_LIST`와 `TICKER_NAMES`에도 추가 (DataCollector가 수집해야 함)
3. 백필 스크립트로 과거 30일 데이터 적재:

```bash
# 스크립트의 NEW_TICKERS_US 또는 NEW_TICKERS_KR에 추가 후 실행
python3 scripts/backfill_swing_tickers.py
```

4. `sam build --use-container && sam deploy` 재배포

## 제외 종목 이력

| 티커 | 제외 사유 | 제외일 |
|---|---|---|
| LMT | PBR 구조적 고평가 (min 10.18), 조건 충족 불가 | 2026-04-26 |
| BRK-B | PBR 데이터 0.0009 왜곡 (수동 검증 필요) | 2026-04-26 |
| PARA | 상장폐지 (Skydance Media 합병 소멸) | 2026-04-26 |
