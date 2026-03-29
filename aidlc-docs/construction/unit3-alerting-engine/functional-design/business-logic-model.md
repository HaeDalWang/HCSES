# Unit 3: AlertingEngine - Business Logic Model

## 실행 흐름

```
handler(event, context)
  │
  ├─ [BR-04] webhook_url = get_discord_webhook_url()  ← 전역 캐시
  │
  ├─ ticker, market, breakdown, current_price_value = parse_event(event)
  │
  ├─ [BR-02] target_price_value  = calc_target_price(current_price_value, pbr_median, pbr_value)
  ├─ [BR-02] stop_loss_price_value = calc_stop_loss_price(current_price_value, pbr_min, pbr_value)
  │
  ├─ [BR-01] message = format_alert_message(...)
  │
  ├─ [BR-03] message = truncate_if_needed(message, limit=2000)
  │
  └─ [BR-05] send_discord_alert(webhook_url, message)  ← 최대 3회 재시도
```

## 목표가 / 손절가 계산

```python
def calc_target_price(price_value, pbr_median_value, pbr_value) -> str:
    if not pbr_value or pbr_value == 0:
        return "N/A"
    return str(round(price_value * (pbr_median_value / pbr_value), 0))

def calc_stop_loss_price(price_value, pbr_min_value, pbr_value) -> str:
    if not pbr_value or pbr_value == 0:
        return "N/A"
    return str(round(price_value * (pbr_min_value / pbr_value), 0))
```

## 메시지 포맷 (정상)

```
🚨 [HCSES 알람] 005930.KS (KR)
━━━━━━━━━━━━━━━━━━━━
현재가:   ₩75,000
목표가:   ₩92,000  (+22.7%)
손절가:   ₩61,000  (-18.7%)
━━━━━━━━━━━━━━━━━━━━
📊 스코어: 100.0 / 100
  • Valuation Floor: 40점
  • Momentum Pivot:  30점
  • Supply/Demand:   30점
━━━━━━━━━━━━━━━━━━━━
🔍 감지된 시그널:
  • ValuationFloor: PBR(0.55) <= MinPBR*1.1(0.55)
  • MomentumPivot: Price(75000)>MA20(70000), RSI 28→36
  • SupplyDemand: CumNetBuy -100→500 (양전 전환)
━━━━━━━━━━━━━━━━━━━━
📅 2026-03-29
```
