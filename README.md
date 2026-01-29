# Agent-VI

**가치투자 철학 기반 AI 기업 분석 에이전트**

Agent-VI는 Deep Value와 Quality 투자 철학을 적용하여 한국 주식(KOSPI/KOSDAQ)을 분석하고 보고서를 자동 생성하는 멀티 에이전트 시스템입니다.

## 주요 특징

### 🎯 투자 철학 기반 분석
- **Deep Value**: 자산가치 대비 저평가 기업 발굴 (안전마진, NCAV, 그레이엄 넘버)
- **Quality**: 우수 기업을 합리적 가격에 매수 (경제적 해자, 경영진 품질, 성장성)

### 🤖 멀티 에이전트 파이프라인
- **정보 수집 에이전트**: DART 공시, 네이버 뉴스, YouTube, 블로그 분석
- **재무 분석 에이전트**: 재무제표, 주가 데이터, 밸류에이션 지표 계산
- **가치투자 평가 에이전트**: Knowledge Base 기반 Deep Value + Quality 평가
- **보고서 생성 에이전트**: 최종 보고서 작성 및 웹 게시

### 📚 유연한 지식 관리
- 투자 철학을 마크다운 파일(`knowledge/*.md`)로 관리
- 사용자가 직접 편집 가능, 다음 분석부터 자동 반영
- 특정 대가에 종속되지 않아 자유롭게 발전

### ⚡ 병렬 처리 & 재개 가능
- LangGraph로 정보 수집과 재무 분석을 동시 실행
- PostgreSQL 체크포인팅으로 실패 시 마지막 성공 지점부터 재개

## 기술 스택

- **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic
- **Frontend**: Next.js 15 (App Router, ISR) + Tailwind CSS
- **Agent Framework**: LangGraph 1.0+ (with PostgreSQL checkpointing)
- **LLM**: LiteLLM (OpenAI, Anthropic 등 멀티 프로바이더)
- **Database**: PostgreSQL 16
- **Scheduler**: APScheduler
- **Data Sources**: OpenDartReader (DART), pykrx (주가), Naver API, YouTube Data API

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

- `DART_API_KEY`: [DART OpenAPI](https://opendart.fss.or.kr) 발급
- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`: [Naver Developers](https://developers.naver.com)
- `YOUTUBE_API_KEY`: Google Cloud Console에서 발급
- `OPENAI_API_KEY` 또는 `ANTHROPIC_API_KEY`: LLM 프로바이더 키

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

### 5. 기업 등록 및 분석 실행

1. http://localhost:3000/companies 에서 관심 기업 등록
2. http://localhost:3000/admin 에서 분석 실행
3. 생성된 보고서는 http://localhost:3000/reports 에서 확인

## 프로젝트 구조

```
agent-vi/
├── knowledge/                  # 투자 철학 Knowledge Base
│   ├── deep_value.md           # 자산가치 중심 투자 원칙
│   └── quality.md              # 기업 품질/성장 중심 투자 원칙
├── backend/
│   └── app/
│       ├── agents/             # LangGraph 에이전트 파이프라인
│       ├── db/models/          # SQLAlchemy 모델
│       ├── api/v1/             # FastAPI 라우터
│       ├── data_sources/       # 외부 API 클라이언트
│       ├── llm/                # LiteLLM 프로바이더
│       └── scheduler/          # APScheduler 작업
├── frontend/
│   └── src/
│       ├── app/                # Next.js 페이지 (App Router)
│       ├── components/         # React 컴포넌트
│       └── lib/                # API 클라이언트, 타입 정의
└── docs/
    └── architecture.md         # 상세 아키텍처 문서
```

## 투자 철학 커스터마이징

`knowledge/` 디렉토리의 마크다운 파일을 편집하여 투자 원칙을 변경할 수 있습니다:

```bash
# 에디터로 직접 편집
vim knowledge/deep_value.md
vim knowledge/quality.md

# 또는 웹 UI에서 편집
# http://localhost:3000/admin/knowledge
```

다음 분석 실행부터 변경된 원칙이 자동 반영됩니다.

## 스케줄링

APScheduler로 주기적 작업을 자동화할 수 있습니다:

```bash
# 스케줄러를 별도 프로세스로 실행
docker compose --profile full up
```

기본 스케줄:
- **일일 주가 업데이트**: 평일 18:00 KST
- **일일 뉴스 스캔**: 평일 08:00, 14:00 KST
- **주간 전체 분석**: 매주 토요일 09:00 KST
- **분기 재무 업데이트**: 1/4/7/10월 15일

## 개발

### 백엔드 개발

```bash
cd backend

# 의존성 설치
pip install -e ".[dev]"

# 개발 서버 실행
uvicorn app.main:app --reload

# 테스트 실행
pytest

# 코드 포매팅
ruff format .

# 마이그레이션 생성
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### 프론트엔드 개발

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 린트
npm run lint
```

## API 문서

백엔드가 실행 중일 때 다음 주소에서 자동 생성된 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 라이선스

MIT License

## 참고 문서

### 프로젝트 문서
- [TODO.md](./TODO.md) - 할 일 체크리스트 (현재 작업 상태)
- [ROADMAP.md](./ROADMAP.md) - 구현 로드맵 (Phase 1~6)
- [아키텍처 문서](./docs/architecture.md) - 시스템 설계 상세

### 외부 문서
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [DART OpenAPI 가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001)
- [pykrx 문서](https://github.com/sharebook-kr/pykrx)

---

**Agent-VI** - 가치투자 철학과 AI를 결합한 기업 분석 솔루션
