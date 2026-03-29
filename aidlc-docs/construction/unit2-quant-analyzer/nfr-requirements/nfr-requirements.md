# Unit 2: QuantAnalyzer - NFR Requirements

## 성능
- Lambda 메모리: 256MB (DynamoDB 조회 + 계산 위주, 대용량 데이터 로드 없음)
- 타임아웃: 300초 (50종목 × 최대 5초 = 250초 여유)
- 하루 최대 20회 실행 (KR 10회 + US 10회)

## 신뢰성
- 개별 종목 분석 실패 격리 (Bulkhead)
- `data_status=COMPLETE` 데이터만 참조 (TC-05)
- `analysis_status=DONE` 재계산 방지 (멱등성)
- 시장 운영 시간 외 실행 시 graceful exit

## 보안 (Security Extension 전체 적용)
- SECURITY-03: 구조화 로깅, 스코어 결과 로그 허용 (민감 데이터 아님)
- SECURITY-06: Lambda Role — DynamoDB 읽기 + AlertingEngine Invoke 권한만
- SECURITY-15: 전역 예외 핸들러, fail-closed (조건 모호 시 0점)

## 비용
- DynamoDB PAY_PER_REQUEST (기존 테이블 재사용)
- Lambda 호출 비용: 하루 20회 × 300초 × 256MB → 월 약 $0.5 미만
