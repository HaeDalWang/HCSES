# HCSES 요구사항 명확화 질문

requirement.md를 분석하였습니다. 시스템 구축 전 아래 질문들에 답변해 주세요.
각 질문의 `[Answer]:` 태그 뒤에 선택한 알파벳을 입력해 주세요.

---

## Question 1
대상 종목의 범위는 어떻게 됩니까?

A) 한국 주식 시장만 (KOSPI, KOSDAQ)
B) 미국 주식 시장만 (NYSE, NASDAQ)
C) 한국 + 미국 주식 시장 모두
D) 기타 (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 2
모니터링할 종목 수는 어느 정도입니까?

A) 소규모 (50종목 이하)
B) 중규모 (50~200종목)
C) 대규모 (200~500종목)
D) 기타 (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
Quant Analyzer의 실행 주기 "Daily 10x"는 어떤 의미입니까?

A) 하루에 10번 균등 간격으로 실행 (예: 9시, 10시, 11시...)
B) 장 중 특정 시간대에만 실행 (예: 장 시작, 장 마감 전후)
C) 데이터 수집 후 즉시 분석 실행 (이벤트 기반)
D) 기타 (please describe after [Answer]: tag below)

[Answer]: D) 주식 시장 개장 시간(09:00~15:30) 내에 실시간 가격 변동과 기술적 지표(Pivot)를 포착하기 위해 전략적으로 분산 실행함을 의미합니다.

---

## Question 4
백테스팅 기능을 이번 구현 범위에 포함합니까?

A) 예, 백테스팅 스크립트도 함께 구현
B) 아니오, 실시간 운영 시스템만 먼저 구현
C) 기타 (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
Telegram 알람 외에 추가 알림 채널이 필요합니까?

A) Telegram만으로 충분
B) 이메일 알림도 추가
C) Slack 알림도 추가
D) 기타 (please describe after [Answer]: tag below)

[Answer]: D) 텔레그램이 아닌 우선 Discord로만 진행

---

## Question 6
DynamoDB TTL 설정 관련 - Raw Data 보존 기간을 어떻게 설정합니까?

A) 1년 (365일) - requirement.md 기본값
B) 6개월 (180일)
C) 2년 (730일)
D) 기타 (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 7
AWS 배포 환경은 어떻게 됩니까?

A) 단일 AWS 계정, 단일 리전 (ap-northeast-2 서울)
B) 단일 AWS 계정, 복수 리전
C) 복수 AWS 계정 (dev/prod 분리)
D) 기타 (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 8
목표가 및 손절가 계산 방식을 확인합니다. requirement.md에 명시된 방식 외 추가 계산 로직이 있습니까?

A) 없음 - 목표가: PBR Median 기반, 손절가: PBR Min 기반만 사용
B) 추가 계산 로직 있음 (예: ATR 기반 손절, 이동평균 기반 목표가)
C) 기타 (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 9
스코어링 시스템의 가중치 배분을 어떻게 설정합니까?

A) Valuation Floor 50점 + Momentum Pivot 50점 (합계 100점, 90점 이상 알람)
B) 각 조건별 세분화된 가중치 직접 정의 필요
C) 기타 (please describe after [Answer]: tag below)

[Answer]: B) 각 조건별 세분화된 가중치 직접 정의 필요

상세 배분:
1. Valuation Floor (PBR): 40점
2. Momentum Pivot (RSI/MA): 30점
3. Supply/Demand (수급): 30점
- Global Kill-Switch: 가중치 합산과 별개로 작동하며, 활성화 시 최종 Score를 강제로 0점 처리하는 Blocking Logic으로 구현합니다.

---

## Question 10
공휴일/휴장일 처리 방식은 어떻게 합니까?

A) 휴장일에는 Lambda 자체를 실행하지 않음 (EventBridge 스케줄 조정)
B) Lambda는 실행하되 데이터 없으면 graceful skip 처리
C) 기타 (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 11 (Security Extension)
보안 확장 규칙을 이 프로젝트에 적용합니까?

A) 예 - 모든 SECURITY 규칙을 블로킹 제약으로 적용 (프로덕션 수준 권장)
B) 아니오 - SECURITY 규칙 생략 (PoC/프로토타입 수준)
C) 기타 (please describe after [Answer]: tag below)

[Answer]: A) Secrets Manager를 통한 필요한 토큰/인증 키 등 관리

---

모든 질문에 답변 후 완료되었다고 알려주세요.
