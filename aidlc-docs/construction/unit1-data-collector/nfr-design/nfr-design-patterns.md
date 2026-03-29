# Unit 1: DataCollector - NFR Design Patterns

## 패턴 1: Bulkhead (격벽) — 종목별 실패 격리
각 종목 수집을 독립 try/except 블록으로 감싸 단일 종목 실패가 전체 실행에 영향 없도록 격리.

```python
results = {"success": [], "failed": [], "skipped": []}
for ticker in tickers:
    try:
        record = collect_stock_data(ticker, market, today)
        if record:
            save_stock_daily(record)
            results["success"].append(ticker)
        else:
            results["skipped"].append(ticker)
    except Exception as e:
        logger.warning(f"ticker={ticker} collection_failed error={str(e)}")
        mark_as_failed(ticker, today)
        results["failed"].append(ticker)
```

## 패턴 2: Retry with Exponential Backoff — 외부 API 재시도
yfinance, FinanceDataReader, pandas_datareader 호출 실패 시 최대 3회 재시도.

```python
def with_retry(fn, max_attempts=3, base_delay=2.0):
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
```

## 패턴 3: Idempotent Write — 멱등성 쓰기 (TC-01)
DynamoDB PutItem에 ConditionExpression 적용. 이미 COMPLETE 레코드 존재 시 skip.

```python
condition = "attribute_not_exists(ticker) OR #ds = :failed"
# FAILED 상태는 재시도 허용
```

## 패턴 4: Global Error Handler — 전역 예외 처리 (SECURITY-15)
Lambda handler 최상단에 전역 try/except. 미처리 예외 발생 시 안전한 응답 반환.

## 패턴 5: Structured Logging — 구조화 로그 (SECURITY-03)
```python
logger.info(json.dumps({
    "timestamp": datetime.utcnow().isoformat(),
    "correlation_id": context.aws_request_id,
    "level": "INFO",
    "market": market,
    "ticker": ticker,
    "message": "collection_complete",
    "data_status": "COMPLETE"
}))
# 민감 데이터(API 키, 토큰) 절대 로그 출력 금지
```
