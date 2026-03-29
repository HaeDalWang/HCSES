# HCSES - Unit Test Execution

## 전체 단위 테스트 실행
```bash
source .venv/bin/activate
PYTHONPATH=. pytest tests/unit/ -v --tb=short
```

## 커버리지 포함 실행
```bash
PYTHONPATH=. pytest tests/unit/ -v --cov=src --cov-report=term-missing --cov-report=html
```

## 모듈별 개별 실행

### shared 모듈
```bash
PYTHONPATH=. pytest tests/unit/shared/ -v
```
- `test_models.py` — 데이터클래스 기본값 검증
- `test_market_calendar.py` — 주말/공휴일, DST, 시장 시간
- `test_scoring.py` — Kill-Switch (stale 포함), Valuation, Momentum, Supply/Demand, 통합 스코어

### DataCollector
```bash
PYTHONPATH=. pytest tests/unit/data_collector/ -v
```
- `test_ingestion_service.py` — RSI (Wilder's), MA20, 볼린저, 정규화
- `test_handler.py` — Bulkhead, 휴장일 skip, 전역 예외

### QuantAnalyzer
```bash
PYTHONPATH=. pytest tests/unit/quant_analyzer/ -v
```
- `test_handler.py` — 시장 시간, Kill-Switch, Bulkhead, 알람 실패 시 PENDING 유지

### AlertingEngine
```bash
PYTHONPATH=. pytest tests/unit/alerting_engine/ -v
```
- `test_alert_service.py` — 가격 계산, KR/US 포맷, 2000자 제한, Discord 재시도
- `test_handler.py` — 성공/실패, Webhook 누락, 전역 예외

### Backtesting
```bash
PYTHONPATH=. pytest tests/unit/backtesting/ -v
```
- `test_backtest_runner.py` — 수익률 계산, Kill-Switch 억제, CSV 출력
- `test_seed_migrator.py` — CONSERVATIVE_FACTOR 검증, 결측 처리

## 예상 결과
- 총 테스트: 약 45개
- 전체 통과 (0 failures)
- 외부 API mock 처리 (yfinance, DynamoDB, Discord)
