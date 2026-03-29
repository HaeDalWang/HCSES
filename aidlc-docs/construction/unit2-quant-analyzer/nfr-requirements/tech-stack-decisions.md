# Unit 2: QuantAnalyzer - Tech Stack Decisions

| 항목 | 선택 | 근거 |
|---|---|---|
| 런타임 | Python 3.12 | 요구사항 명시 |
| AWS SDK | boto3 | DynamoDB 조회, Lambda Invoke |
| 시간대 처리 | pytz | DST 감지 (shared/market_calendar.py 재사용) |
| 스코어링 로직 | shared/scoring.py | Unit 4 Backtesting과 코드 공유 |
| 로깅 | Python logging + JSON | 구조화 로그 |
| 배포 | AWS SAM | template.yaml에 추가 |
