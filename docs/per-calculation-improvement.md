# PER 계산 로직 개선 보고서

**날짜**: 2026-02-06
**대상 종목**: SK (034730)
**문제**: 분기 재무정보에서 PER 누락

---

## 문제 상황

SK의 분기 재무정보를 조회했을 때 다음 분기들의 PER이 NULL로 표시됨:
- 2025년 1Q, 2Q, 3Q
- 2024년 2Q, 3Q

PBR은 모든 분기에 정상적으로 표시되었으나, PER만 선택적으로 누락.

---

## 원인 분석

### 기존 PER 계산 로직

[financial_service.py:274-366](backend/app/services/financial_service.py#L274-L366)의 `update_per_pbr` 함수:

1. **Q4/연간 PER**: 시가총액 / net_income으로 직접 계산
2. **Q1-Q3 PER**: pykrx `get_market_fundamental`에서 trailing PER 가져옴

### 근본 원인

**pykrx에서 SK의 fundamentals 데이터를 가져올 수 없음** (403 Forbidden 에러).

```python
fund_df = stock_client.get_fundamentals_range(stock_code, min_date, max_date)
# ❌ SK (034730): fund_df is None or empty
```

pykrx는 모든 종목의 fundamentals를 제공하지 않거나, 특정 종목/시점에 데이터가 없을 수 있음.

기존 코드는 pykrx fundamentals 실패 시 아무것도 하지 않아 PER이 NULL로 남음.

---

## 해결 방법

### 3단계 Fallback 로직 구현

[financial_service.py:353-404](backend/app/services/financial_service.py#L353-L404)

#### 1차: pykrx Fundamentals Trailing PER (가장 정확)

```python
fund_df = stock_client.get_fundamentals_range(stock_code, min_date, max_date)
if fund_df is not None and not fund_df.empty:
    per_val = fund_df.loc[valid_dates[-1]].get("PER")
    if pd.notna(per_val) and float(per_val) != 0:
        updates[(year, quarter)]["per"] = float(per_val)
```

- pykrx에서 제공하는 trailing PER (과거 12개월 실적 기준)
- 가장 정확하지만, 모든 종목/시점에 제공되지 않음

#### 2차: 시가총액 기반 연환산 PER

```python
if has_cap_data:
    market_cap = cap_df.loc[valid_dates[-1], "market_cap"]
    annualized_income = net_income * 4  # 분기 순이익 * 4
    calculated_per = market_cap / annualized_income
```

- pykrx `get_market_cap`에서 시가총액 조회 가능하면 사용
- 분기 순이익을 4배하여 연환산 (trailing 근사치)
- 순이익이 양수일 때만 계산

#### 3차: PBR 역산 기반 PER

```python
# PBR = 시가총액 / 자본총계
# → 시가총액 = PBR * 자본총계
market_cap = pbr * total_equity
annualized_income = net_income * 4
calculated_per = market_cap / annualized_income
```

- 시가총액도 가져올 수 없을 때의 최후 수단
- 이미 계산된 PBR (또는 DB에 저장된 PBR)을 활용
- SK의 경우 이 방법으로 PER 계산 성공

---

## 적용 결과

### SK (034730) PER 데이터 복구

| 분기 | 매출액(조) | 순이익(조) | PER | PBR | 계산 방법 |
|------|-----------|-----------|-----|-----|-----------|
| 2025Q3 | 31 | 2.7 | **1.42** | 0.18 | PBR 역산 |
| 2025Q2 | 30 | 1.0 | **3.79** | 0.19 | PBR 역산 |
| 2025Q1 | 31 | 3.6 | **0.65** | 0.12 | PBR 역산 |
| 2024Q3 | 30 | 1.1 | **2.42** | 0.14 | PBR 역산 |
| 2024Q2 | 31 | 0.5 | **6.32** | 0.14 | PBR 역산 |
| 2024Q1 | 33 | 0.7 | 9.14 | 0.16 | pykrx (기존) |

---

## 향후 영향

### 다른 종목 대응

이제 새로운 종목을 추가할 때 pykrx fundamentals가 없어도 자동으로 PER이 계산됨:

1. **삼성전자, SK하이닉스 등 대형주**: pykrx fundamentals 정상 → 1차 방법 사용
2. **중소형주 또는 특수 종목**: pykrx fundamentals 없음 → 2차/3차 fallback 자동 작동
3. **모든 경우**: 최소한 PBR이 있으면 PER도 계산 가능

### 로깅 강화

```
INFO: pykrx fundamentals 없음: 034730 - 분기 PER을 연환산으로 계산합니다
INFO: 034730 2025Q3 PER PBR역산: 1.42 (PBR: 0.18, 자본: 85,911,105,000,000, 순이익*4: 10,719,956,000,000)
```

각 fallback 단계에서 어떤 방법으로 계산되었는지 로그에 기록되어 디버깅 용이.

---

## 기술적 세부사항

### 연환산 PER의 정확도

- **Trailing 12M PER** (이상적): 과거 4개 분기 순이익 합계 사용
- **단일 분기 연환산** (fallback): 해당 분기 순이익 * 4

단일 분기 연환산은 계절성/일회성 요인을 반영하지 못하므로 trailing보다 덜 정확하지만, 데이터가 없는 것보다는 유용함.

### PBR 역산 방식의 한계

- PBR이 이미 계산되어 있어야 함 (대부분의 경우 pykrx 시가총액으로 계산 가능)
- PBR이 오래된 시점의 데이터라면 시가총액 역산 값도 부정확할 수 있음
- 그러나 최신 데이터에 대해서는 충분히 신뢰할 수 있는 근사치 제공

---

## 체크리스트

- [x] SK PER 누락 원인 파악
- [x] pykrx fundamentals 접근 불가 확인
- [x] 3단계 fallback 로직 구현
- [x] SK PER 데이터 복구
- [x] 백엔드 재시작 및 테스트
- [x] 문서화

---

## 관련 파일

- [backend/app/services/financial_service.py](backend/app/services/financial_service.py) — `update_per_pbr` 함수 수정
- [backend/app/data_sources/stock_client.py](backend/app/data_sources/stock_client.py) — pykrx 래퍼
- [test_sk_per_debug.py](test_sk_per_debug.py) — 디버깅 스크립트 (참고용)
