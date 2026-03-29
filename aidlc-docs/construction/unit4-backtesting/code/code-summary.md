# Unit 4: Backtesting - Code Summary

## 생성된 파일
- `src/backtesting/backtest_runner.py` — CLI 진입점, 히스토리컬 데이터 로드, 스코어링 시뮬레이션, 수익률 계산, CSV 리포트
- `src/backtesting/seed_migrator.py` — PBR 통계 생성 및 StockStatsTable 마이그레이션
- `tests/unit/backtesting/test_backtest_runner.py` — 수익률 계산, 시뮬레이션, 리포트 테스트

## 실행 방법
```bash
# 백테스팅 실행
python -m src.backtesting.backtest_runner \
  --tickers 005930.KS 000660.KS \
  --market KR \
  --start 2021-01-01 \
  --end 2023-12-31

# Seed Data 생성 포함
python -m src.backtesting.backtest_runner \
  --tickers 005930.KS AAPL \
  --market KR \
  --start 2018-01-01 \
  --end 2025-12-31 \
  --seed
```

## 적용된 제약사항
- BR-01 (shared/scoring.py 재사용), BR-02 (FDR 캐시 fallback), BR-03 (Kill-Switch)
- BR-04 (60/90/150거래일 수익률), BR-05 (Seed 마이그레이션), BR-06 (CSV 리포트)
- Look-ahead bias 방지: rolling PBR min 사용
- EC-01 (KR PBR 결측 FDR 캐시), EC-02 (변수명 규칙)
