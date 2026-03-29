# HCSES 추가 명확화 질문

Q9 답변에서 **Supply/Demand (수급) 30점** 항목이 언급되었으나, requirement.md에는 해당 지표가 정의되어 있지 않습니다. 구현 전 명확히 해야 합니다.

---

## Clarification Question 1
Supply/Demand (수급) 지표는 구체적으로 어떤 데이터를 사용합니까?

A) 외국인/기관 순매수 데이터 (FinanceDataReader로 수집 가능한 한국 시장 한정)
B) 거래량 급증 비율 (현재 거래량 vs 20일 평균 거래량)
C) 공매도 잔고 비율 (Short Interest Ratio)
D) 기타 (please describe after [Answer]: tag below)

[Answer]: A) 외국인/기관 순매수 데이터

논리적 근거: 한국 시장(KRX)은 종목별 투자자별 순매수 데이터를 일 단위로 투명하게 공개합니다. FinanceDataReader를 통해 수집되는 외국인 및 기관의 **'20거래일 누적 순매수합'**이 양수(+)로 전환되는 시점은 밸류에이션 바닥 확인 후 추세 반등의 강력한 기술적 근거가 됩니다.

---

## Clarification Question 2
수급 지표는 한국 시장과 미국 시장 모두에 동일하게 적용합니까?

A) 예, 동일한 로직 적용 (데이터 가용성에 따라 fallback 처리)
B) 아니오, 한국 시장에만 수급 지표 적용 (미국은 Valuation+Momentum 70점 만점으로 재조정)
C) 기타 (please describe after [Answer]: tag below)

[Answer]: B) 아니오, 한국 시장에만 수급 지표 적용

논리적 근거: 미국 시장은 한국과 달리 기관/외국인의 일일 매매 동향을 실시간으로 공시하지 않습니다(13F 보고서는 분기별 지연 공시). 따라서 미국 주식(US)의 경우 수급 지표(30점)를 제외하고, 대신 Valuation Floor 가중치를 60점, Momentum Pivot 가중치를 40점으로 상향 조정하여 필터링 강도를 유지합니다. 데이터가 불확실한 지표를 억지로 대입하는 것보다 가용한 데이터의 가중치를 높이는 것이 엔지니어링 측면에서 신뢰도가 더 높습니다.

---

답변 후 완료되었다고 알려주세요.
