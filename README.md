# Agent-VI

**한국 주식 재무실적 뷰어**

Agent-VI는 KOSPI/KOSDAQ 종목의 재무제표를 간편하게 조회하고 분석할 수 있는 웹 애플리케이션입니다.

## 주요 기능

### 📈 종목 등록 & 자동완성
- 종목명 또는 종목코드로 검색
- 실시간 자동완성으로 정확한 종목 선택
- DART API를 통한 자동 기업정보 조회

### 💼 재무실적 조회
- **연간 실적**: 최근 6년 (매출액, 영업이익, 순이익)
- **분기 실적**: 최근 8분기 (매출액, 영업이익, 순이익)
- 억 원 단위 표시 및 전년 대비 증감률 표시

### 🔄 증분 데이터 수집
- 한 번 수집한 데이터는 DB에 저장
- 재수집 시 새로운 데이터만 추가로 가져옴
- 중복 데이터 방지 및 빠른 조회

## 기술 스택

- **Backend**: FastAPI + SQLAlchemy 2.0 + PostgreSQL
- **Frontend**: Next.js 15 (App Router) + Tailwind CSS
- **Data Sources**:
  - DART API (OpenDartReader) - 재무제표
  - pykrx - 주가 데이터
  - Naver API - 뉴스/블로그 (향후 기능)

## 빠른 시작

### 사전 요구사항

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. 저장소 클론

```bash
git clone <repository-url>
cd agent-vi
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 필수 API 키를 입력하세요:

- `DART_API_KEY`: [DART OpenAPI](https://opendart.fss.or.kr) 발급 (필수)
- `OPENAI_API_KEY`: (선택) AI 분석 기능 사용 시

### 3. Docker Compose로 실행

```bash
docker compose up
```

서비스가 시작되면:
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **프론트엔드**: http://localhost:3000

### 4. 데이터베이스 마이그레이션

```bash
# 백엔드 컨테이너에서 실행
docker compose exec backend alembic upgrade head
```

## 사용 방법

### 종목 등록

1. http://localhost:3000/companies 접속
2. "+ 종목 등록" 버튼 클릭
3. 종목명 또는 종목코드 입력 (예: "삼성전자", "005930")
4. 자동완성 목록에서 선택
5. 등록 버튼 클릭

등록 후 백그라운드에서 재무데이터가 자동으로 수집됩니다.

### 재무실적 조회

1. 종목 목록에서 "상세 보기" 클릭
2. 연간 실적 표 확인 (최근 6년)
3. 분기 실적 표 확인 (최근 8분기)

## 프로젝트 구조

```
agent-vi/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API 엔드포인트
│   │   │   ├── stocks.py     # 종목 검색
│   │   │   ├── companies.py  # 종목 CRUD
│   │   │   └── financials.py # 재무제표 조회
│   │   ├── services/         # 비즈니스 로직
│   │   │   └── financial_service.py  # 재무데이터 수집
│   │   ├── data_sources/     # 외부 데이터 소스
│   │   │   ├── dart_client.py        # DART API
│   │   │   └── stock_client.py       # pykrx
│   │   └── db/models/        # SQLAlchemy 모델
│   └── alembic/              # DB 마이그레이션
├── frontend/
│   └── src/
│       ├── app/
│       │   └── companies/
│       │       ├── page.tsx           # 종목 목록
│       │       └── [stock_code]/page.tsx  # 상세 페이지
│       ├── components/companies/
│       │   ├── CompanyCreateModal.tsx  # 등록 모달
│       │   └── FinancialTable.tsx      # 재무표
│       └── lib/
│           ├── api.ts        # API 클라이언트
│           └── types.ts      # TypeScript 타입
└── docker-compose.yml
```

## API 엔드포인트

### 종목 검색
```
GET /api/v1/stocks/search?q=삼성
```

### 종목 등록
```
POST /api/v1/companies
{
  "stock_code": "005930",
  "company_name": "삼성전자",
  "market": "KOSPI"
}
```

### 재무제표 조회
```
GET /api/v1/financials/005930?years=6
```

### 재무데이터 재수집
```
POST /api/v1/financials/005930/refresh?force=false
```

## 향후 계획

### Phase 6: 데이터 시각화
- 재무 트렌드 차트 (Recharts)
- 주가 차트
- 밸류에이션 지표 시각화

### Phase 7: AI 분석 기능
- 가치투자 철학 기반 자동 분석
- LangGraph 멀티 에이전트 파이프라인
- 투자 보고서 자동 생성

자세한 로드맵은 [ROADMAP.md](./ROADMAP.md)를 참조하세요.

## 문제 해결

### DART 기업코드 조회 실패
- 종목코드가 정확한지 확인하세요.
- DART API 키가 올바르게 설정되었는지 확인하세요.

### 재무데이터가 표시되지 않음
- 종목 등록 직후에는 데이터 수집에 수 분이 소요될 수 있습니다.
- 잠시 후 페이지를 새로고침해주세요.

### PostgreSQL 연결 오류
```bash
# 데이터베이스 재시작
docker compose restart db
```

## 라이선스

MIT License

## 기여

이슈 및 PR은 언제나 환영합니다!

## 문의

프로젝트 관련 문의사항은 GitHub Issues를 이용해주세요.
