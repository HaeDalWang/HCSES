# Unit 1: DataCollector - Deployment Architecture

## 배포 환경
- 리전: ap-northeast-2 (서울)
- 계정: 단일 AWS 계정
- 배포 도구: AWS SAM CLI

## 배포 순서
1. `sam build`
2. `sam deploy --guided` (최초) / `sam deploy` (이후)
3. DynamoDB 테이블 자동 생성 (SAM 스택)
4. Secrets Manager 수동 생성 (Discord Webhook URL)
5. Unit 4 Backtesting 실행 → StockStatsTable Seed Data 마이그레이션
6. EventBridge Rules 자동 활성화

## 보안 컴플라이언스 요약 (Unit 1)

| Rule | 상태 | 비고 |
|---|---|---|
| SECURITY-01 | 준수 | DynamoDB SSE 활성화 |
| SECURITY-02 | N/A | 네트워크 중간자 없음 (Lambda → DynamoDB 직접) |
| SECURITY-03 | 준수 | 구조화 로깅, 민감 데이터 제외 |
| SECURITY-04 | N/A | 웹 애플리케이션 없음 |
| SECURITY-05 | N/A | 외부 API 엔드포인트 없음 |
| SECURITY-06 | 준수 | Lambda Role 최소 권한, 특정 테이블 ARN만 |
| SECURITY-07 | N/A | VPC 미사용 (Lambda 퍼블릭 엔드포인트) |
| SECURITY-08 | N/A | 사용자 인증 없음 (내부 자동화) |
| SECURITY-09 | 준수 | 기본 자격증명 없음, 오류 메시지 내부 노출 없음 |
| SECURITY-10 | 준수 | requirements.txt 버전 고정, lock 파일 사용 |
| SECURITY-11 | 준수 | Rate Limiting 적용, 보수적 원칙 |
| SECURITY-12 | 준수 | IAM Role 사용, 하드코딩 자격증명 없음 |
| SECURITY-13 | N/A | 외부 스크립트/CDN 없음 |
| SECURITY-14 | 준수 | CloudWatch 로그 보존 90일, 알람 설정 |
| SECURITY-15 | 준수 | 전역 예외 핸들러, fail-closed |
