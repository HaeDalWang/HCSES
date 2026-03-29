# Unit 4: Backtesting - NFR Requirements

- 실행 환경: 로컬 CLI (Lambda 아님)
- 실행 시간: 50종목 × 5년 기준 약 10~30분 허용 (Rate Limiting 포함)
- FDR 로컬 캐시: `~/.fdr_cache/` 활용으로 반복 실행 시 속도 향상
- Look-ahead bias 방지: rolling PBR min 사용
- 보안: AWS 자격증명은 환경변수 또는 AWS CLI 프로파일 사용 (하드코딩 금지)
- 결과 파일: CSV 출력, 민감 데이터 미포함
