# Unit 2: QuantAnalyzer - NFR Design Patterns

## 패턴 1: Fail-Closed (보수적 원칙)
모든 스코어링 함수에서 데이터 결측 또는 조건 모호 시 0점 반환.
`if any(v is None for v in [...]):  return 0.0`

## 패턴 2: Bulkhead — 종목별 실패 격리
```python
for ticker in tickers:
    try:
        result = run_analysis(ticker, market)
        if result.total_score >= 90:
            invoke_alerting_engine(result)
    except Exception as e:
        logger.warning(f"analysis_failed ticker={ticker} error={str(e)}")
        continue  # 다음 종목 계속
```

## 패턴 3: Idempotent Analysis — 재계산 방지 (TC-05)
분석 완료 후 즉시 `analysis_status=DONE` 업데이트.
동일 Lambda 재실행 시 DONE 레코드는 자동 skip.

## 패턴 4: Early Exit — Kill-Switch 및 시장 시간 검증
불필요한 DynamoDB 조회 방지를 위해 Kill-Switch와 시장 시간을 루프 진입 전 선행 평가.

## 패턴 5: Structured Logging (SECURITY-03)
```python
logger.info(json.dumps({
    "timestamp": ..., "correlation_id": ...,
    "ticker": ticker, "market": market,
    "total_score": breakdown.total_score,
    "signals": breakdown.signals
}))
```
