# 금융위원회 공공데이터 API 설정 가이드

재무정보 페이지의 PER/PBR 계산을 위해 금융위원회 공공데이터 API를 사용합니다.

---

## 1. API 키 발급 (무료, 5분 소요)

### 1.1 공공데이터포털 회원가입

1. https://www.data.go.kr/ 접속
2. 상단 "회원가입" 클릭
3. 개인회원 또는 기업회원 선택 후 가입

### 1.2 API 활용 신청

1. 로그인 후 검색창에 **"금융위원회_주식시세정보"** 입력
2. 검색 결과에서 **"금융위원회_주식시세정보"** 클릭
3. **"활용신청"** 버튼 클릭
4. 활용 목적 입력 (예: "개인 프로젝트 재무 분석")
5. 즉시 승인됨 (심사 없음)

### 1.3 서비스 키 확인

1. 우측 상단 **"마이페이지"** → **"오픈API"** 클릭
2. 활용 중인 API 목록에서 **"금융위원회_주식시세정보"** 찾기
3. **"일반 인증키(Encoding)"** 복사

---

## 2. 환경변수 설정

프로젝트 루트의 `.env` 파일에 서비스 키를 추가합니다:

```bash
PUBLIC_DATA_SERVICE_KEY=your_service_key_here
```

**주의**: `.env` 파일은 gitignored되어 있으므로 로컬에서만 생성하세요.

---

## 3. 서비스 재시작

Docker Compose를 사용하는 경우:

```bash
docker compose restart backend
```

로컬 개발 환경:

```bash
# backend/ 디렉토리에서
uvicorn app.main:app --reload
```

---

## 4. 작동 확인

### 4.1 로그 확인

백엔드 로그에서 "시가총액: 금융위원회" 메시지를 확인합니다:

```bash
docker logs agent-vi-backend-1 | grep "시가총액"
```

**예상 출력**:
```
INFO - ✓ 시가총액: 금융위원회 (005930, 8/8건)
INFO - PER/PBR 업데이트 완료: 005930 (8건)
```

### 4.2 수동 갱신 테스트

종목의 재무 데이터를 수동으로 갱신해봅니다:

```bash
curl -X POST http://localhost:8000/api/v1/financials/005930/refresh
```

### 4.3 DB 확인

PER/PBR 값이 정상적으로 계산되었는지 확인:

```bash
docker exec agent-vi-db-1 psql -U postgres -d agent_vi -c \
  "SELECT fiscal_year, fiscal_quarter, \
          ROUND(CAST(per AS numeric), 2) as per, \
          ROUND(CAST(pbr AS numeric), 2) as pbr \
   FROM financial_statements \
   WHERE company_id = (SELECT id FROM companies WHERE stock_code = '005930') \
   ORDER BY fiscal_year DESC, fiscal_quarter DESC LIMIT 8;"
```

### 4.4 프론트엔드 확인

브라우저에서 http://localhost:3000/companies/005930 접속하여 PER/PBR 값이 표시되는지 확인합니다.

---

## 5. API 제한사항

### 호출 제한
- **초당**: 10건
- **일**: 10,000건

### 데이터 지연
- **D+1**: 전일 데이터까지 제공
- 예: 2026년 2월 6일에는 2026년 2월 5일까지의 데이터 조회 가능

### 캐싱
- 과거 데이터는 불변이므로 LRU 캐시(최대 5,000건)에 영구 저장
- 중복 조회 시 API 호출 없이 캐시에서 반환
- 호출 제한 문제 없음

---

## 6. Fallback 동작

금융위원회 API 실패 시 자동으로 pykrx로 전환됩니다:

```
1차: 금융위원회 API
  ↓ (실패 시)
2차: pykrx (기존 방식)
```

**로그 예시**:
```
WARNING - 금융위원회 API 실패: ... → pykrx fallback
INFO - ✓ 시가총액: pykrx fallback (005930, 8건)
```

---

## 7. 문제 해결

### API 키가 작동하지 않는 경우

1. 키가 정확히 복사되었는지 확인 (공백 포함 여부)
2. "일반 인증키(Encoding)" 사용 확인 ("Decoding"이 아님)
3. 공공데이터포털에서 API 활용 승인 상태 확인

### "시가총액 데이터 없음" 경고

다음 중 하나:
- 해당 날짜에 데이터가 없음 (휴장일, 상장 전 등)
- 종목명 매핑이 없음 → `public_data_client.py`의 `_get_stock_name()` 함수에 추가 필요

### 종목명 추가 방법

`backend/app/data_sources/public_data_client.py` 파일의 `_get_stock_name()` 함수에 종목 추가:

```python
stock_names = {
    "005930": "삼성전자",
    "034730": "SK",
    "000660": "SK하이닉스",
    # 여기에 종목 추가
    "123456": "새종목명",
}
```

또는 DB에서 자동 조회하도록 개선 (TODO).

---

## 8. 참고 링크

- 공공데이터포털: https://www.data.go.kr/
- 주식시세정보 API: https://www.data.go.kr/data/15094808/openapi.do
- 기술문서: API 상세페이지에서 "기술문서" 다운로드

---

## 변경 이력

- 2026-02-06: 최초 작성
