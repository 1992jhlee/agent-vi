# 재무 지표 수집 및 계산 가이드

각 재무 항목의 데이터 출처, XBRL 태그, 계산 방식을 정리합니다.

---

## 데이터 출처

| 출처 | 사용 항목 | 클라이언트 |
|------|-----------|------------|
| DART (금융위원회) | 재무제표 전체 (손익/상태표/현금흐름) | `dart_client.py` |
| pykrx (KRX) | PER, PBR | `stock_client.py` |
| 프론트엔드 계산 | 비율 및 파생 지표 | `FinancialTable.tsx` |

---

## 손익계산서

| 항목 | XBRL account_id | sj_div |
|------|-----------------|--------|
| 매출액 | `ifrs-full_Revenue` | IS, CIS |
| 영업이익 | `dart_OperatingIncomeLoss` | IS, CIS |
| 순이익 | `ifrs-full_ProfitLoss` | IS, CIS |

---

## 재무상태표

| 항목 | XBRL account_id | sj_div |
|------|-----------------|--------|
| 총자산 | `ifrs-full_Assets` | BS |
| 총부채 | `ifrs-full_Liabilities` | BS |
| 총자본 | `ifrs-full_Equity` | BS |
| 유동자산 | `ifrs-full_CurrentAssets` | BS |
| 유동부채 | `ifrs-full_CurrentLiabilities` | BS |
| 재고자산 | `ifrs-full_Inventories` | BS |

### 프론트엔드 계산 지표

- **부채비율** = `총부채 / 총자본 × 100` (%)
- **당좌비율** = `(유동자산 - 재고자산) / 유동부채 × 100` (%)

---

## 현금흐름표

| 항목 | XBRL account_id | sj_div |
|------|-----------------|--------|
| 영업활동현금흐름 | `ifrs-full_CashFlowsFromUsedInOperatingActivities` | CF |
| 투자활동현금흐름 | `ifrs-full_CashFlowsFromUsedInInvestingActivities` | CF |
| 재무활동현금흐름 | `ifrs-full_CashFlowsFromUsedInFinancingActivities` | CF |

### CAPEX (설비투자)

**1단계 — 단일 태그 매칭:**
`ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` (CF)

**2단계 — Fallback (단일 태그 미사용 시):**
일부 회사는 유형자산 취득을 세부 항목으로 분리하여 신고합니다. 이 경우 아래 태그들을 합산합니다:

| 세부 태그 | 항목 |
|-----------|------|
| `dart_PurchaseOfLand` | 토지 |
| `dart_PurchaseOfMachinery` | 기계장치 |
| `dart_PurchaseOfStructure` | 구축물 |
| `dart_PurchaseOfVehicles` | 차량운반구 |
| `dart_PurchaseOfOtherPropertyPlantAndEquipment` | 기타유형자산 |
| `dart_PurchaseOfConstructionInProgress` | 건설중인자산 |
| `dart_PurchaseOfBuildings` | 건물 |

> 예시: DL이앤씨(375500)는 단일 태그를 사용하지 않아 fallback 합산으로 수집됨.

### 잉여현금흐름 (FCF)

프론트엔드 계산: `FCF = 영업활동현금흐름 - CAPEX`

capex가 `null`이면 FCF도 표시되지 않음.

---

## 투자지표

### 프론트엔드 계산

| 지표 | 계산식 |
|------|--------|
| ROE | `순이익 / 총자본 × 100` (%) |
| ROA | `순이익 / 총자산 × 100` (%) |
| 영업이익률 | `영업이익 / 매출액 × 100` (%) |
| 순이익률 | `순이익 / 매출액 × 100` (%) |

### PER / PBR (DB 저장)

기간말 날짜 기준 가장 가까운 거래일 이하의 시가총액을 사용하여 직접 계산합니다.
- Q1: 3월 31일, Q2: 6월 30일, Q3: 9월 30일, Q4(연간): 12월 31일

**PBR — 모든 기간에서 직접 계산:**
- 출처: pykrx `get_market_cap_by_date` (단일 범위 호출)
- 계산식: `시가총액 / total_equity`
- `total_equity ≤ 0`이면 `null`

**PER — Q4(연간)와 Q1-Q3에서 다르게 처리:**
- **Q4(연간):** `시가총액 / net_income`으로 직접 계산 (당해연도 실적 기반)
  - 이미 완료된 과거 연간에서도 실제 당해 실적을 사용하여 정확한 값 제공
  - 음수 순이익이면 음수 PER로 저장·표시 (적자 여부를 직관적으로 파악 가능)
  - `net_income == 0`이면 `null` (0으로 나누기 불가)
- **Q1-Q3:** pykrx `get_market_fundamental_by_date`의 trailing PER 사용
  - DART 분기 실적은 YTD 누적값이므로 단순 연산으로 연간화 불가
  - 음수 PER도 그대로 저장, `PER == 0`이면 `null`

> 참고: pykrx의 trailing PER는 해당 날짜 시점의 **전행 12개월 실적**을 기준으로 계산됩니다.
> Q4 종료일 시점에서는 아직 당해연도 실적이 공시되지 않았을 수 있어 전년도 실적으로 계산될 수 있기 때문에,
> Q4는 실제 실적 기반 직접 계산을 사용합니다.

- **정밀도:** PostgreSQL `Float`(단일정밀도) 저장 → 표시 시 `toFixed()`로 반올림 (예: 0.9599… → "0.96배")

---

## 단위 및 표시 규칙

- 금액 항목: 원단위 저장, 프론트엔드에서 **억원** 단위로 변환 표시 (`÷ 100,000,000`)
- 비율 항목: `%` 단위, 소수점 1자리
- PER/PBR: `배` 단위 (PER 1자리, PBR 2자리)
- 미발표 분기: 값이 `null`이고 현재 날짜 기준 아직 발표되지 않은 기간이면 "(발표 전)"로 표시
