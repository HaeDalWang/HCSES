# 모니터링 대상 종목 (Tickers)

본 시스템은 Valuation Floor(역사적 PBR 하단) 및 Momentum Pivot 로직과의 수학적 정합성이 검증된 22개 종목으로 한정하여 운영됩니다.
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

---

## 미국 시장 (US) — 11종목

| 티커 | 종목명 | 편입 사유 |
|---|---|---|
| META | Meta | 빅테크 중 유일 편입 (과거 실적 쇼크 시 PBR 하단 터치 이력 검증) |
| MU | Micron Technology | 메모리 반도체 사이클 (PBR 저점 반등 패턴 극명) |
| AMD | Advanced Micro Devices | 비메모리 반도체 사이클 |
| AMAT | Applied Materials | 반도체 장비 사이클 (꾸준한 BPS 증가 및 중간 빈도 알람 타겟) |
| JPM | JPMorgan Chase | 상업 은행 대표주 (안정적인 자산 가치) |
| GS | Goldman Sachs | 투자 은행 (JPM과 동조화되지 않는 별도의 IB 사이클 확보) |
| XOM | ExxonMobil | 에너지 사이클 대표주 |
| CVX | Chevron | 에너지 사이클 대표주 |
| UNH | UnitedHealth Group | 헬스케어 방어주 (JNJ 대비 적절한 주가 변동성 확보) |
| LMT | Lockheed Martin | 방산업 (수주 기반의 안정적 BPS 및 지정학적 리스크 헤지) |
| BRK-B | Berkshire Hathaway | 거시 경제 패닉 감지 (시스템적 투매 발생 시 Black Swan 지표용) |

---

## 종목 추가 방법

`src/data_collector/handler.py`의 `TICKER_LIST`와 `TICKER_NAMES`에 동시 추가 후,
신규 종목 Seed Data 생성 필수:

```bash
PYTHONPATH=. python -m src.backtesting.backtest_runner \
  --tickers [NEW_TICKER] \
  --market [KR|US] \
  --start 2019-01-01 --end 2025-12-31 --seed
```

이후 `sam build --use-container && sam deploy` 재배포.
