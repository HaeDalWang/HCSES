# Unit 3: AlertingEngine - Business Rules

## BR-01: 알람 메시지 필수 포함 항목
- 종목명 / 티커 / 시장
- 현재가 (current_price_value)
- 목표가 (target_price_value) — PBR Median 기반
- 손절가 (stop_loss_price_value) — PBR Min 기반
- 감지된 시그널 목록 (signals)
- 최종 스코어 및 각 지표별 점수

## BR-02: 목표가 / 손절가 계산
- 목표가: `current_price_value * (pbr_median_value / pbr_value)`
- 손절가: `current_price_value * (pbr_min_value / pbr_value)`
- pbr_value = 0 또는 None → 계산 불가, "N/A" 표시

## BR-03: Discord 2,000자 제한 (TC-03)
- 메시지 길이 > 2,000자 시 요약 버전으로 대체
- 요약: 종목명, 현재가, 스코어, 시그널 수만 포함
- 초과 여부 WARNING 로그 기록

## BR-04: Secrets Manager 캐싱 (TC-02)
- Discord Webhook URL은 전역 변수로 캐싱
- Lambda 컨텍스트 재사용 시 API 재호출 금지

## BR-05: Discord 발송 재시도
- 실패 시 최대 3회 재시도 (지수 백오프: 1s, 2s, 4s)
- 3회 모두 실패 시 ERROR 로그 후 실패 반환

## BR-06: 민감 데이터 로그 금지 (SECURITY-03)
- Webhook URL 절대 로그 출력 금지
- 발송 성공/실패 여부만 로그
