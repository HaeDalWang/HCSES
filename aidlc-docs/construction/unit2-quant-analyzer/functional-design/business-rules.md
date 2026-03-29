# Unit 2: QuantAnalyzer - Business Rules

## BR-01: 보수적 원칙
조건이 하나라도 모호하거나 데이터 결측 시 False(0점) 반환. True를 반환하지 않음.

## BR-02: Global Kill-Switch (가중치와 별개)
다음 중 하나라도 해당하면 Kill-Switch 활성화 → 최종 score 강제 0점:
- `vix_value > 30`
- `yield_change_pct > 3.0` (US10Y 전일 대비 변동률 %)
- `krwusd_value > krwusd_bb_upper_value` (환율 상단 볼린저 돌파)
데이터 결측 시 해당 조건은 False 처리 (보수적 원칙 예외 — Kill-Switch는 데이터 없으면 미발동).

## BR-03: Valuation Floor
- 조건: `pbr_value <= pbr_min_value * 1.1`
- `pbr_value` 또는 `pbr_min_value` 결측 시 → 0점 (BR-01)
- 점수: KR=40점, US=60점

## BR-04: Momentum Pivot
- 조건: `close_value > ma20_value` AND `rsi_prev_level <= 30` AND `rsi_curr_level > 35`
- 어느 값이라도 None → 0점 (BR-01)
- 점수: KR=30점, US=40점

## BR-05: Supply/Demand (KR only)
- 조건: `cumulative_net_buy_value > 0` AND `prev_cumulative_net_buy_value <= 0` (양전 전환)
- US 시장 → 항상 0점
- 데이터 결측 → 0점 (BR-01)
- 점수: 30점

## BR-06: analysis_status 관리 (TC-05 확장)
- 분석 전: `data_status=COMPLETE AND analysis_status=PENDING` 레코드만 처리
- 분석 완료 후: `analysis_status=DONE` 업데이트 → 장 중 재계산 방지

## BR-07: 알람 임계값
- `total_score >= 90` AND `kill_switch.active == False` → AlertingEngine 호출

## BR-08: DST 및 시장 운영 시간 검증
- Lambda 실행 시 현재 시각이 해당 시장 운영 시간 내인지 확인
- 운영 시간 외 실행 시 조기 종료 (정상)

## BR-09: 20거래일 누적 순매수합 계산
- StockDailyTable에서 최근 20거래일 `foreign_net_buy_value + institution_net_buy_value` 합산
- 결측값은 0으로 처리 (누적합 계산 한정 — 개별 값 대체와 구분)
