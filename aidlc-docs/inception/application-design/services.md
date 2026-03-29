# HCSES - Service Layer

## Service 1: DataIngestionService

**역할**: DataCollector Lambda의 오케스트레이션 레이어

**책임**:
- 종목 목록 순회 및 수집 조율
- Rate Limiting 적용 (종목 간 sleep)
- 수집 결과 집계 및 data_status 최종 업데이트
- 오류 발생 종목 격리 (전체 실패 방지)

**흐름**:
```
EventBridge → handler()
  → load_ticker_list(market)
  → for each ticker:
      → is_market_holiday() → skip if True
      → collect_stock_data(ticker)
      → normalize_numeric_fields()   ← 정규화 (소수점 4자리)
      → save_stock_daily()
      → collect_kr_supply_demand() [KR only]
      → sleep(random.uniform(1,3))
  → collect_market_indicators() → save_market_indicator()
```

---

## Service 2: ScoringService

**역할**: QuantAnalyzer Lambda의 스코어링 파이프라인 오케스트레이션

**책임**:
- 시장 운영 시간 및 DST 검증
- Kill-Switch 선행 평가 (활성화 시 전체 분석 중단)
- 종목별 분석 실행 및 결과 집계
- 90점 이상 종목 AlertingEngine 호출

**흐름**:
```
EventBridge (KR/US 별도) → handler()
  → detect_dst_offset(market)
  → is_within_market_hours() → exit if False
  → evaluate_global_kill_switch() → exit if active
  → for each ticker:
      → get_latest_complete_data()   ← analysis_status != 'DONE' 필터
      → skip if None
      → run_analysis(ticker, market)
      → mark_analysis_done()         ← 재계산 방지
      → if total_score >= 90: invoke AlertingEngine
```

---

## Service 3: AlertDeliveryService

**역할**: AlertingEngine Lambda의 메시지 생성 및 발송 오케스트레이션

**책임**:
- Secrets Manager 캐싱 관리
- 메시지 포맷 및 길이 검증
- Discord 발송 및 재시도

**흐름**:
```
Invoke (from QuantAnalyzer) → handler()
  → get_discord_webhook_url() [캐시 우선]
  → calculate_target_price()
  → calculate_stop_loss_price()
  → format_alert_message()
  → truncate_message_if_needed()
  → send_discord_alert() [최대 3회 재시도]
```

---

## Service 4: BacktestingService

**역할**: Backtesting 스크립트의 실행 파이프라인

**책임**:
- 히스토리컬 데이터 로드 및 스코어링 시뮬레이션
- 수익률 계산 및 리포트 생성
- Seed Data 생성 및 DynamoDB 마이그레이션

**흐름**:
```
CLI → run_backtest(tickers, start_date, end_date, market)
  → load_historical_data()
      ↳ KR 종목 PBR 결측 시 FDR 로컬 캐시 fallback (~/.fdr_cache/)
  → simulate_scoring() → list[AlertSignal]
  → for each signal:
      → calculate_forward_returns([60, 90, 150])
  → generate_seed_data() → migrate_seed_data()
  → export_report()
```

---

## Service 5: StatsRefreshService

**역할**: StatsUpdater Lambda의 주간 통계 갱신 오케스트레이션

**흐름**:
```
EventBridge (매주 토요일) → handler()
  → for each ticker:
      → recalculate_pbr_stats()
      → update_stats_table()
      → sleep(random.uniform(1,3))
```
