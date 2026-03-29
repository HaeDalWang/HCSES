# HCSES - Application Design (통합)

## 시스템 개요

High-Confidence Stock Entry Scanner는 5개 컴포넌트와 5개 서비스 레이어로 구성된 서버리스 퀀트 스캐닝 시스템입니다.

---

## 컴포넌트 구성

| 컴포넌트 | 유형 | 트리거 | 유닛 |
|---|---|---|---|
| DataCollector | AWS Lambda | EventBridge Daily Cron | Unit 1 |
| QuantAnalyzer | AWS Lambda | EventBridge KR/US Market Hours | Unit 2 |
| AlertingEngine | AWS Lambda | Lambda Invoke (QuantAnalyzer) | Unit 3 |
| Backtesting | Python Script | CLI 수동 실행 | Unit 4 |
| StatsUpdater | AWS Lambda | EventBridge 매주 토요일 | Unit 1 (부속) |

---

## 핵심 설계 결정

### 1. data_status + analysis_status 기반 Race Condition 및 재계산 방지
DataCollector가 수집 완료 시 `data_status = COMPLETE`로 업데이트.
QuantAnalyzer는 `data_status = COMPLETE AND analysis_status != DONE` 레코드만 참조.
분석 완료 후 `analysis_status = DONE`으로 업데이트하여 장 중 10회 실행 시 불필요한 재계산 방지.

### 2. 시장별 EventBridge 분리
- `KR_Collector`: 매일 16:30 KST (07:30 UTC)
- `US_Collector`: 매일 22:30 KST (13:30 UTC, EDT 기준)
- `KR_Analyzer`: 장 중 분산 (09:00~15:30 KST)
- `US_Analyzer`: 장 중 분산 (13:30~20:00 UTC, DST 반영)

### 3. 공유 scoring 모듈
QuantAnalyzer와 Backtesting이 동일한 `scoring.py` 모듈을 재사용하여 백테스팅 결과의 신뢰성 보장.

### 4. 보수적 원칙 적용
모든 스코어링 함수에서 조건 모호 시 False(0점) 반환. 데이터 결측 시 분석 skip.

### 5. 시장별 차등 스코어링
DataIngestionService에서 모든 수치를 소수점 4자리로 반올림.
yfinance와 FinanceDataReader 간 정밀도 차이로 인한 스코어링 오차 방지.

### 7. Backtesting KR PBR 결측 처리
Unit 4 한정으로 FinanceDataReader 로컬 DB 캐싱(`~/.fdr_cache/`) 활용.
yfinance KR PBR 결측 시 FDR 캐시로 fallback하여 백테스팅 데이터 완결성 확보.
- KR: Valuation(40) + Momentum(30) + Supply/Demand(30) = 100점
- US: Valuation(60) + Momentum(40) = 100점
- 공통: Global Kill-Switch 활성화 시 강제 0점

---

## 상세 문서 참조

- 컴포넌트 정의: `components.md`
- 메서드 시그니처: `component-methods.md`
- 서비스 레이어: `services.md`
- 의존성 매트릭스: `component-dependency.md`
