# Unit 3: AlertingEngine - NFR Requirements

- 메모리: 128MB (HTTP 호출 위주)
- 타임아웃: 30초
- 보안: SECURITY-03 (Webhook URL 로그 금지), SECURITY-12 (Secrets Manager), SECURITY-15 (전역 예외)
- 신뢰성: 3회 재시도, 지수 백오프
- 비용: QuantAnalyzer 호출 시에만 실행 (월 1~2회 예상)
