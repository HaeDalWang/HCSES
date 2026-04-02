# HCSES 운영 계획서 v1.0
> High-Confidence Stock Entry Scanner — US 시장 단독 운영 기준

---

## 1. 시스템 개요

| 항목 | 내용 |
|------|------|
| 목적 | US 시장 저평가 + 기술적 반등 구간 포착 → Discord 알림 수신 → 매수 판단 |
| 대상 시장 | US (NYSE / NASDAQ) 단독 |
| 운영 종목 수 | 11종목 |
| 알림 채널 | Discord Webhook |
| 인프라 | AWS Lambda + DynamoDB + EventBridge (SAM) |
| 예상 알림 빈도 | 월 1~2회 (고확신 신호만) |

---

## 2. 운영 종목 리스트

```python
TICKER_LIST = {
    "US": [
        "META",   # Meta Platforms
        "MU",     # Micron Technology
        "AMD",    # Advanced Micro Devices
        "AMAT",   # Applied Materials
        "JPM",    # JPMorgan Chase
        "GS",     # Goldman Sachs
        "BRK-B",  # Berkshire Hathaway  ⚠️ PBR 0.0 이슈 — Seed Data 수동 검증 필요
        "XOM",    # ExxonMobil
        "CVX",    # Chevron
        "UNH",    # UnitedHealth Group
        "LMT",    # Lockheed Martin     ⚠️ PBR 구조적 고평가 — 알림 빈도 낮을 수 있음
    ]
}
```

### 티커 → 회사명 매핑 (알림 메시지용)

```python
TICKER_NAME_MAP = {
    "META":  "Meta Platforms",
    "MU":    "Micron Technology",
    "AMD":   "Advanced Micro Devices",
    "AMAT":  "Applied Materials",
    "JPM":   "JPMorgan Chase",
    "GS":    "Goldman Sachs",
    "BRK-B": "Berkshire Hathaway",
    "XOM":   "ExxonMobil",
    "CVX":   "Chevron",
    "UNH":   "UnitedHealth Group",
    "LMT":   "Lockheed Martin",
}
```

---

## 3. 스코어링 로직 (기존 HCSES 유지)

### US 시장 가중치
```
Valuation Floor  : 60점
Momentum Pivot   : 40점
─────────────────────────
합계              : 100점
알림 임계값       : score >= 90
```

### Valuation Floor (60점)
```
조건: current_PBR <= pbr_min_value × 1.1
충족 시: 60점 / 미충족: 0점
```

### Momentum Pivot (40점)
```
조건: Price > MA20
  AND RSI_prev <= 30
  AND RSI_curr  > 35

RSI = Wilder's Smoothing (ewm, alpha=1/14)
충족 시: 40점 / 미충족: 0점
```

### Global Kill-Switch

```
VIX 구간별 동작:
  VIX > 30          → score 강제 0 (알림 완전 차단)
  25 < VIX <= 30    → score 유지 + 알림에 ⚠️ 경고 문구 추가
  VIX <= 25         → 정상

stale 지표 시 (전일 데이터 사용):
  VIX > 27          → score 강제 0
  23 < VIX <= 27    → 경고 문구 추가

US10Y 변동률:
  > 3%              → score 강제 0
  stale 시: > 2%    → score 강제 0
```

경고 문구 예시:
```
⚠️ VIX 경고 구간 ({vix:.1f}) — 시장 변동성 높음
   포지션 절반만 진입 고려 (정상 10% → 5%)
```

설계 의도: VIX 25~30은 지정학적 리스크 등으로 시장이 불안하지만
붕괴는 아닌 회색지대. 이 구간에서 PBR 저점 + 모멘텀 반등 패턴이
오히려 자주 발생하므로 완전 차단 대신 경고로 처리.

---

## 4. 수식 정의 (코딩 Agent 전달용)

```python
# ATR 14일 (Average True Range)
# True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
ATR14 = TrueRange.ewm(alpha=1/14, min_periods=14).mean()

# 손절가 (변동성 기반)
stop_loss = current_price - (2 * ATR14)

# 목표가 (PBR 중앙값 복귀)
target_price = current_price * (pbr_median / current_pbr)

# 1차 익절 (목표가의 70% 도달 시)
partial_exit = target_price * 0.7

# 종목당 매수금액
position_size = total_budget * 0.10

# 타임컷
time_cut = entry_date + timedelta(days=60)
```

---

## 5. Discord 알림 포맷

### 포맷 스펙

```
🚨 매수 신호 | {회사명} ({티커}) | {거래소}

━━━━━━━━ 진입 근거 ━━━━━━━━
현재가:         ${current_price}
HCSES 점수:     {score} / 100
  └ Valuation:  {valuation_score} (PBR Floor 충족)
  └ Momentum:   {momentum_score} (RSI {rsi_prev:.0f}→{rsi_curr:.0f} 돌파)

PBR 현재:       {current_pbr:.2f}x
PBR 역사 최저:  {pbr_min:.2f}x
PBR 중앙값:     {pbr_median:.2f}x

━━━━━━━━ 얼마나 살까 ━━━━━━━━
ATR(14):        ${atr14:.2f}
종목당 한도:    총 예산의 10%

━━━━━━━━ 출구 전략 ━━━━━━━━
손절가:  ${stop_loss:.2f}  (현재가 - 2×ATR)   → {stop_pct:+.1f}%
1차익절: ${partial_exit:.2f}  (목표가의 70%)     → {partial_pct:+.1f}%
목표가:  ${target_price:.2f}  (PBR 중앙값 기준)  → {target_pct:+.1f}%
타임컷:  매수일로부터 60일 내 미달성 시 전량 매도

━━━━━━━━ 시장 상태 ━━━━━━━━
VIX:     {vix:.1f} (정상)
US10Y:   {us10y:.2f}% (정상)
신호일:  {signal_datetime} ET
```

### 실제 예시 (MU 기준)

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

## 6. 매수/매도 운영 규칙

### 규칙 1 — 포지션 사이징
```
종목당 매수금액  = 총 예산의 10%
동시 보유 최대   = 5종목
현금 유보 비율   = 최소 50% 유지 (다음 알림 대기)
```

### 규칙 2 — 매수 실행
```
- 알림 수신 당일 장 마감 전 매수 (종가 근처)
- 같은 날 복수 알림 시 → HCSES 점수 높은 종목 1개만 매수
- 현재 보유 5종목이면 → 기존 포지션 정리 후 매수 검토
```

### 규칙 3 — 손절 (예외 없음)
```
- 손절가(현재가 - 2×ATR) 터치 시
- 다음날 장 시작 후 30분 내 무조건 매도
- 이유 불문, 예외 없음
```

### 규칙 4 — 익절
```
- 1차 익절: 목표가의 70% 도달 시 → 보유량의 50% 매도
- 최종 익절: 목표가 도달 시 → 잔여 전량 매도
- 타임컷:   매수 후 60일 경과, 목표가 50% 미달성 시 → 전량 매도
```

### 규칙 5 — 확인 주기
```
- 매일 장 마감 후 보유 종목 손절가/목표가 확인
- Discord 알림 수신 즉시 확인
```

---

## 7. 코딩 Agent 구현 지시사항

### 즉시 패치 (배포 전)

**① scoring_service.py — ATR 기반 손절가 계산 추가**
```
- DataCollector가 수집한 OHLCV 데이터로 ATR14 계산
- 기존 PBR 기반 손절가 제거
- stop_loss = current_price - (2 * ATR14) 로 교체
- AlertingEngine으로 atr14, stop_loss 값 전달
```

**② alert_service.py — 알림 포맷 전면 수정**
```
- 제목 형식: "🚨 매수 신호 | {TICKER_NAME_MAP[ticker]} ({ticker}) | {exchange}"
- exchange: NASDAQ 또는 NYSE (종목별 하드코딩 또는 yfinance info에서 추출)
- 위 섹션 5의 포맷 스펙 그대로 구현
- 1차익절(partial_exit), 타임컷(60일) 항목 추가
```

**③ quant_analyzer — Kill-Switch 로직 변경**
```
기존: VIX > 25 → score 강제 0
변경:
  VIX > 30       → score 강제 0 (완전 차단)
  25 < VIX <= 30 → score 유지, 알림에 ⚠️ 경고 문구 추가
  VIX <= 25      → 정상

stale 지표 시:
  VIX > 27       → score 강제 0
  23 < VIX <= 27 → 경고 문구 추가
```

### DynamoDB 추가 (선택, V1.5)
```
- PortfolioTable: 현재 보유 종목 트래킹
  - ticker, entry_price, entry_date, stop_loss, target_price, partial_exit
- 보유 5종목 초과 시 알림에 ⚠️ 경고 문구 추가
```

---

## 8. 배포 전 체크리스트

- [ ] ATR 기반 손절가 패치 완료 (2× ATR 확인)
- [ ] Kill-Switch VIX 로직 변경 완료 (30 차단 / 25~30 경고)
- [ ] 알림 포맷 수정 완료 (회사명 + 티커 + 거래소 제목)
- [ ] BRK-B Seed Data 수동 검증 (PBR 0.0 이슈)
- [ ] 22개 종목 BPS 검증 스크립트 실행 결과 이상 없음 확인
- [ ] backtest_runner.py --seed 실행 (DynamoDB Seed Data 적재)
- [ ] 백테스팅 결과 확인 (연간 알림 발생 횟수 검토)
- [ ] AWS SAM 배포

---

## 9. 한 달 운영 후 판단 기준 (V2 검토)

| 관측 항목 | 기준 | 조치 |
|-----------|------|------|
| 알림 발생 횟수 | 월 0회 | RSI 임계값 완화 검토 (30→35, 35→40) |
| yfinance 수집 실패율 | 5% 초과 | Alpha Vantage fallback 추가 |
| BPS 왜곡 의심 알림 | 1건 이상 | DART/SEC 크로스체크 로직 추가 |
| 손절가 너무 빈번 | 3회 이상 | ATR 배수 2× → 2.5× 조정 검토 |

---

## 10. 참고 — 이 시스템으로 할 수 없는 것

- 매수 타이밍의 완벽한 보장 (확률을 높일 뿐, 손실 가능성은 항상 존재)
- 뉴스/공시 기반 악재 필터링 (V2 백로그)
- 실시간 포트폴리오 수익률 추적 (V2 백로그)

> 이 시스템은 "언제 볼 것인가"를 알려줍니다.
> "살지 말지"는 위 운영 규칙을 따르세요.