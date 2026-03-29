# Unit 3: AlertingEngine - Code Summary

## 생성된 파일
- `src/alerting_engine/alert_service.py` — 가격 계산, 메시지 포맷, 2000자 제한, Discord 발송 (3회 재시도)
- `src/alerting_engine/handler.py` — Lambda 핸들러 (Secret 캐싱, 전역 예외 처리)
- `template.yaml` — AlertingEngineFunction 추가 (128MB, 30초, Secrets Manager 권한)
- `tests/unit/alerting_engine/test_alert_service.py` — 가격 계산, 포맷, 2000자, 재시도 테스트
- `tests/unit/alerting_engine/test_handler.py` — 성공/실패/Webhook 누락/전역 예외 테스트

## 적용된 제약사항
- BR-01~06 전체
- TC-02 (Secret 캐싱), TC-03 (2000자 제한)
- SECURITY-03 (Webhook URL 로그 금지), SECURITY-06 (최소 권한), SECURITY-15 (전역 예외)
