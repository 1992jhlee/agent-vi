# 재무 데이터 갭 분석 보고서

종목코드: 034730
종목명: SK
분석 시각: 2026-02-06
분석자: 재무 데이터 무결성 전문 에이전트

---

## 1. 현재 DB 상태

### 1.1 업데이트 이전 상태 (2026-02-06 분석 시점)

| 연도 | 분기 | 타입 | PER | PBR | 매출액 (원) |
|------|------|------|-----|-----|-------------|
| 2025 | 3 | quarterly | NULL | 0.18 | 31,041,366,000,000 |
| 2025 | 2 | quarterly | NULL | 0.19 | 30,141,963,000,000 |
| 2025 | 1 | quarterly | NULL | 0.12 | 31,229,933,000,000 |
| 2024 | 4 | annual | 18.03 | 0.12 | 124,690,439,000,000 |
| 2024 | 3 | quarterly | NULL | 0.14 | 30,637,299,000,000 |
| 2024 | 2 | quarterly | NULL | 0.14 | 31,197,130,000,000 |
| 2024 | 1 | quarterly | 9.14 | 0.16 | 33,026,813,000,000 |
| 2023 | 4 | annual | -32.06 | 0.17 | 131,237,878,000,000 |
| 2023 | 3 | quarterly | 7.48 | 0.13 | 33,864,045,000,000 |
| 2023 | 2 | quarterly | 7.61 | 0.14 | 31,923,219,000,000 |
| 2022 | 4 | annual | 3.53 | 0.20 | 134,551,641,000,000 |
| 2021 | 4 | annual | 3.25 | 0.28 | 98,325,016,000,000 |
| 2020 | 4 | annual | -156.06 | 0.33 | 81,820,139,000,000 |
| **2019** | **4** | **annual** | **NULL** | **NULL** | **99,264,574,000,000** |

### 1.2 확인된 갭

#### 갭 1: 2019년 연간 PER/PBR 누락
- 기간: 2019년 4분기 (연간)
- 누락 항목: PER, PBR
- 매출액 및 순이익 데이터는 존재

#### 갭 2: 2024/2Q 이후 분기 PER 누락
- 기간: 2024/2Q, 2024/3Q, 2025/1Q, 2025/2Q, 2025/3Q (총 5개 분기)
- 누락 항목: PER
- PBR은 정상적으로 존재

---

## 2. 원인 분석

### 2.1 갭 1 원인: 휴장일 분기 종료일 처리 오류

**상세 분석:**

1. `update_per_pbr` 함수는 분기 종료일을 기준으로 `min_date`와 `max_date`를 설정합니다.
2. 2019년 4분기 종료일은 2019-12-31이지만, 이 날은 **휴장일**입니다.
3. pykrx의 `get_market_cap` API는 영업일만 데이터를 반환하므로, 2019-12-31을 요청하면 **2020-01-02부터 데이터를 반환**합니다.
4. 코드는 `target_dt` 이하의 날짜 중 가장 가까운 날을 찾는데, 2019-12-31보다 이전의 영업일(2019-12-30)이 조회 범위에 포함되지 않아 **PER/PBR 계산 불가**

**코드 위치:**
`backend/app/services/financial_service.py` - `update_per_pbr` 함수, 296-298번째 줄

```python
min_date = min(period_dates.values())  # 예: "20191231"
max_date = max(period_dates.values())
cap_df = stock_client.get_market_cap(stock_code, min_date, max_date)
```

**분류:** 코드 수정 가능 (파싱/수집 로직 버그)

### 2.2 갭 2 원인: pykrx 데이터 소스의 EPS=0 반환

**상세 분석:**

1. 분기별 PER은 `get_fundamentals_range` API를 통해 pykrx의 trailing PER을 가져옵니다.
2. 2024/3Q, 2025/1Q, 2025/2Q, 2025/3Q 기간에 대해 pykrx가 **EPS=0, PER=0**을 반환합니다.
3. 코드는 `float(per_val) != 0` 조건으로 필터링하여 PER=0인 값을 DB에 저장하지 않습니다.
4. 이는 pykrx 측의 데이터 업데이트 지연 또는 SK 종목의 특수한 상황(예: 회계 처리 지연, 분기 실적 미공시 등)으로 추정됩니다.

**검증 결과:**

```
2024/3Q (2024-09-30): PER=0.0, EPS=0.0
2025/1Q (2025-03-31): PER=0.0, EPS=0.0
2025/2Q (2025-06-30): PER=0.0, EPS=0.0
2025/3Q (2025-09-30): PER=0.0, EPS=0.0
```

**분류:** 수정 불가능 (외부 데이터 소스 문제)

---

## 3. 조치 내용

### 3.1 수정 가능: 갭 1 해결 (휴장일 대응 로직 추가)

#### 3.1.1 코드 수정

**파일:** `backend/app/services/financial_service.py`

**변경 사항:**

1. `import` 구문에 `timedelta` 추가:

```python
from datetime import datetime, timedelta
```

2. `update_per_pbr` 함수에서 `min_date`를 30일 앞당기는 로직 추가:

```python
min_date = min(period_dates.values())
max_date = max(period_dates.values())

# 휴장일 대응: min_date를 30일 앞당겨서 분기 종료일이 휴장일인 경우에도
# 이전 영업일의 시가총액 데이터를 포함할 수 있도록 함
# 예: 2019-12-31이 휴장일이면 pykrx는 2020-01-02부터 반환하여 2019-12-30 누락 방지
min_date_dt = datetime.strptime(min_date, "%Y%m%d")
min_date_adjusted = (min_date_dt - timedelta(days=30)).strftime("%Y%m%d")

stock_client = StockClient()

# 시가총액 범위 조회 (단일 API 호출) — PBR 및 Q4 PER 계산용
cap_df = stock_client.get_market_cap(stock_code, min_date_adjusted, max_date)
```

3. 분기별 PER 수집에도 동일하게 `min_date_adjusted` 사용:

```python
fund_df = stock_client.get_fundamentals_range(stock_code, min_date_adjusted, max_date)
```

**설계 결정:**

- 30일을 앞당기는 이유: 대부분의 분기 종료일(3/31, 6/30, 9/30, 12/31)이 주말이나 공휴일에 걸칠 수 있으며, 최악의 경우 연휴가 겹쳐 10일 이상 벌어질 수 있습니다. 30일은 이러한 모든 경우를 안전하게 커버하면서도 과도한 데이터 조회를 피할 수 있는 균형점입니다.
- `min_date_adjusted`는 조회 범위만 확장하며, 실제 PER/PBR 계산은 여전히 `target_dt` (분기 종료일) 이하의 가장 가까운 영업일을 사용하므로 정확도에는 영향이 없습니다.

#### 3.1.2 린팅 검증

```bash
$ docker compose exec -T backend ruff check app/services/financial_service.py
All checks passed!
```

### 3.2 수정 불가능: 갭 2 표시 (pykrx EPS=0 문제)

#### 3.2.1 원인 요약

pykrx 데이터 소스가 2024/2Q 이후 분기에 대해 EPS=0을 반환하여, `update_per_pbr` 함수의 필터링 로직에 의해 DB에 저장되지 않습니다. 이는 다음 중 하나로 추정됩니다:

1. pykrx 측의 데이터 업데이트 지연
2. SK 종목의 특수한 회계 처리 상황 (예: 분기 실적 정정 중, 감사 미완료 등)
3. 외부 데이터 제공자(KRX, DART 등)의 데이터 미제공

#### 3.2.2 메타데이터 기록 전략 (향후 구현 권장)

현재는 코드 수정을 통해 즉시 해결할 수 없으므로, 다음과 같은 개선 사항을 권장합니다:

**1단계: DB에 메타데이터 기록**

`FinancialStatement` 테이블의 `raw_data_json` 컬럼에 다음과 같은 메타데이터를 기록:

```json
{
  "per_unavailable": true,
  "per_unavailable_reason": "pykrx EPS=0 (data source issue)",
  "reported_at": "2026-02-06T12:00:00Z"
}
```

**2단계: 프론트엔드 표시**

`/companies/[stock_code]` 페이지의 분기별 재무실적 테이블에서 해당 기간의 PER 컬럼을 다음과 같이 표시:

- 텍스트: "데이터 미제공" 또는 "N/A"
- 스타일: 회색 또는 경고 색상 (Tailwind CSS의 `text-gray-400` 또는 `text-yellow-600`)
- 툴팁: "외부 데이터 소스의 EPS 정보 미제공"

**구현하지 않은 이유:**

현재 요청 사항은 갭 1 (2019년 PER/PBR 누락)의 수정에 초점이 맞춰져 있으며, 갭 2는 진단 및 보고만 요청되었습니다. 프론트엔드 UI 변경은 별도의 개발 작업이 필요하므로 추가 요청 시 진행합니다.

---

## 4. 검증

### 4.1 수정 후 재수집 및 확인

#### 4.1.1 SK 종목 `update_per_pbr` 재실행

```
종목 정보: SK (034730), company_id=8

=== PER/PBR 업데이트 이전 2019년 데이터 ===
2019년 Q4: PER=NULL, PBR=NULL, 매출액=99,264,574,000,000원

=== update_per_pbr 실행 중 ===

=== PER/PBR 업데이트 이후 2019년 데이터 ===
2019년 Q4: PER=11.47, PBR=0.35, 매출액=99,264,574,000,000원
```

**결과:** 2019년 PER/PBR이 성공적으로 계산되어 DB에 저장되었습니다.

#### 4.1.2 전체 데이터 최종 상태

| 연도 | 분기 | 타입 | PER | PBR |
|------|------|------|-----|-----|
| 2025 | 3 | quarterly | NULL | 0.18 |
| 2025 | 2 | quarterly | NULL | 0.19 |
| 2025 | 1 | quarterly | NULL | 0.12 |
| 2024 | 4 | annual | 18.03 | 0.12 |
| 2024 | 3 | quarterly | NULL | 0.14 |
| 2024 | 2 | quarterly | NULL | 0.14 |
| 2024 | 1 | quarterly | 9.14 | 0.16 |
| 2023 | 4 | annual | -32.06 | 0.17 |
| 2023 | 3 | quarterly | 7.48 | 0.13 |
| 2023 | 2 | quarterly | 7.61 | 0.14 |
| 2022 | 4 | annual | 3.53 | 0.20 |
| 2021 | 4 | annual | 3.25 | 0.28 |
| 2020 | 4 | annual | -156.06 | 0.33 |
| **2019** | **4** | **annual** | **11.47** | **0.35** |

**변경 사항:**
- 2019년 4분기: PER NULL → 11.47, PBR NULL → 0.35 (해결 완료)
- 2024/2Q 이후 분기: PER은 여전히 NULL (pykrx 데이터 소스 문제로 수정 불가)

### 4.2 린팅 결과

```bash
$ docker compose exec -T backend ruff check app/services/financial_service.py
All checks passed!
```

모든 코드 스타일 검사를 통과했습니다.

---

## 5. 요약 및 권장사항

### 5.1 해결된 문제

- **2019년 연간 PER/PBR 누락:** 휴장일 대응 로직 추가로 완전히 해결
- **코드 품질:** 린팅 통과, 주석 추가로 유지보수성 향상

### 5.2 미해결 문제 (외부 요인)

- **2024/2Q 이후 분기 PER 누락:** pykrx 데이터 소스의 EPS=0 반환으로 인한 수집 불가
  - 자동 수정 불가능
  - 데이터 소스 복구 또는 대안 소스 확보 필요

### 5.3 향후 권장사항

#### 5.3.1 단기 (1주 이내)

1. **다른 종목 검증:** SK 외 다른 종목에서도 동일한 패턴이 발생하는지 확인
2. **pykrx 데이터 모니터링:** 2024/2Q 이후 EPS 데이터가 업데이트되는지 주기적으로 확인

#### 5.3.2 중기 (1개월 이내)

1. **메타데이터 기록 시스템 구축:**
   - `raw_data_json`에 데이터 미제공 원인 기록
   - 프론트엔드에서 사용자에게 명확히 표시

2. **대안 데이터 소스 연동:**
   - DART API의 분기별 EPS 데이터 직접 파싱
   - FinanceDataReader 등 다른 라이브러리 검토

3. **알림 시스템:**
   - 데이터 갭 발견 시 관리자에게 자동 알림
   - 주간/월간 데이터 무결성 리포트 생성

#### 5.3.3 장기 (3개월 이내)

1. **데이터 품질 대시보드:**
   - 종목별 데이터 완전성 점수
   - 누락 기간 및 원인 시각화
   - 추세 분석 및 예측

2. **자동 복구 메커니즘:**
   - 데이터 소스 자동 전환
   - 누락 데이터 재시도 스케줄러

---

## 6. 부록

### 6.1 관련 파일

- `/home/plainman/projects/agent-vi/backend/app/services/financial_service.py` (수정됨)
- `/home/plainman/projects/agent-vi/backend/app/data_sources/stock_client.py` (참조)
- `/home/plainman/projects/agent-vi/backend/app/db/models/financial.py` (참조)

### 6.2 참고 자료

- [pykrx 공식 문서](https://github.com/sharebook-kr/pykrx)
- [DART 오픈API](https://opendart.fss.or.kr/)
- [KRX 정보데이터시스템](http://data.krx.co.kr/)

---

**보고서 종료**
