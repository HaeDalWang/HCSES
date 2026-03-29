# Unit 1: DataCollector - NFR Requirements

## 성능 (Performance)
- **실행 시간**: Lambda 최대 실행 시간 15분 이내 (50종목 기준 예상 5~8분)
- **메모리**: 512MB (pandas + yfinance 로드 고려)
- **Rate Limiting**: 종목 간 sleep 1~3초 → 50종목 기준 최대 150초 추가 소요 허용

## 신뢰성 (Reliability)
- **개별 종목 실패 격리**: 단일 종목 수집 실패가 전체 Lambda 실패로 전파되지 않음
- **재시도**: 외부 API 호출 실패 시 최대 3회 재시도 (지수 백오프)
- **공휴일 처리**: 휴장일 graceful skip, 오류 없이 정상 종료
- **FAILED 레코드 재처리**: 다음 실행 시 FAILED 상태 레코드 재시도 허용

## 보안 (Security) — Security Extension 전체 적용
- **SECURITY-12**: AWS 자격증명 하드코딩 금지 → IAM Role (Lambda Execution Role) 사용
- **SECURITY-03**: 구조화된 로깅 (timestamp, correlation_id, level, message). 민감 데이터 로그 출력 금지
- **SECURITY-06**: Lambda Execution Role 최소 권한 (DynamoDB 특정 테이블 읽기/쓰기만)
- **SECURITY-15**: 모든 외부 API 호출에 try/except. 전역 예외 핸들러 필수

## 비용 최적화 (Cost)
- **DynamoDB TTL**: 180일 자동 만료 (StockDailyTable, MarketIndicatorTable)
- **Lambda 호출 횟수**: 하루 2회 (KR/US 각 1회)
- **yfinance 배치 호출**: 가능한 경우 단일 호출로 다수 종목 처리

## 관찰 가능성 (Observability)
- **CloudWatch Logs**: 모든 수집 결과 구조화 로그
- **메트릭**: 수집 성공/실패 종목 수, 실행 시간
- **PBR 결측 경고**: WARNING 레벨 로그 (EC-01)
