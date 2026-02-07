# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 서비스 실행

모든 서비스는 프로젝트 루트에서 Docker Compose로 실행됩니다. PostgreSQL, FastAPI 백엔드, Next.js 프론트엔드가 기본 서비스이며, 스케줄러는 Docker profile로 선택적 실행됩니다.

```bash
# 핵심 서비스 시작 (db + backend + frontend)
docker compose up -d

# 백그라운드 스케줄러 포함 실행
docker compose --profile full up -d

# 특정 서비스 로그 확인
docker logs -f agent-vi-backend-1

# 코드 변경 후 서비스 재시작 (백엔드는 볼륨 마운트로 자동 리로드)
docker compose restart frontend
```

백엔드는 **:8000**, 프론트엔드는 **:3000**, PostgreSQL은 **:5432** 포트를 사용합니다.

### 로컬 개발 (Docker 없이)

**백엔드** — Python 3.11+, PostgreSQL 인스턴스, `.env.example`로부터 생성된 `.env` 파일이 필요합니다:

```bash
cd backend
pip install -e ".[dev]"                        # dev 의존성 포함 설치
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**프론트엔드** — Node 20+가 필요합니다:

```bash
cd frontend
npm install
npm run dev                                   # next dev, :3000에서 실행
```

### 린팅 (Linting)

```bash
cd backend && ruff check .                    # Python 린팅
cd frontend && npm run lint                   # ESLint
```

### 데이터베이스 마이그레이션 (Alembic)

`backend/` 디렉토리에서 실행합니다. 동기 `DATABASE_URL`은 `alembic/env.py`를 통해 `settings`에서 자동으로 읽어옵니다.

```bash
cd backend
alembic revision --autogenerate -m "설명"          # 마이그레이션 생성
alembic upgrade head                               # 마이그레이션 적용
alembic downgrade -1                               # 마이그레이션 되돌리기
```

> 참고: `alembic/env.py`는 `app.db.models`를 와일드카드 임포트하여 autogenerate가 모든 모델을 감지할 수 있도록 합니다. 새 모델을 추가하면 `app/db/models/__init__.py`에서 임포트 가능하도록 해야 합니다.

### 테스트

현재 테스트 스위트가 구성되어 있지 않습니다 (pytest, pytest-asyncio는 dev 의존성에 포함됨). 테스트를 추가하면 `backend/tests/` 디렉토리에 배치하고 다음과 같이 실행합니다:

```bash
cd backend
pytest
```

---

## 아키텍처 개요

### 백엔드 (`backend/`)

**진입점:** `app/main.py` — CORS 미들웨어가 적용된 FastAPI 앱, API 라우터를 단일로 마운트합니다.

**라우팅:** 모든 라우트는 `app/api/router.py`를 통해 `/api/v1` 하위에 있습니다. 각 도메인별로 `app/api/v1/`에 모듈이 있습니다: `stocks`, `companies`, `financials`, `analysis`, `reports`, `health`.

**설정:** `app/config.py` — `.env`를 읽는 Pydantic `Settings` 인스턴스 하나(`settings`)입니다. 다른 모든 모듈은 `from app.config import settings`로 가져옵니다. DART, Naver, OpenAI, Anthropic, 금융위원회 공공데이터의 API 키가 여기에 있습니다.

**데이터베이스 — 세션 패턴 두 가지 (주의):**
- `app/db/session.py`는 **비동기** 엔진(`engine`, `async_session_factory`, `get_db` 의존성)과 **동기** 엔진(`sync_engine`, `sync_session_factory`, `get_sync_session`)을 모두 내보냅니다.
- FastAPI 라우트 핸들러는 `get_db` 의존성을 통해 **비동기** 세션을 사용합니다.
- LangGraph 에이전트 노드는 동기 컨텍스트에서 실행되므로 **동기** 세션(`get_sync_session`)을 사용합니다.
- 두 세션 모두 동일한 PostgreSQL 데이터베이스를 가리키며, 비동기 URL은 `asyncpg`, 동기 URL은 `psycopg2`를 사용합니다.

**데이터 소스 (`app/data_sources/`):** 외부 API의 얇은 래퍼입니다:
- `dart_client.py` — OpenDartReader 기반; DART에서 재무제표를 조회하고 파싱합니다. "매출액" 필드가 없을 때 손익계산서 최상단 수익 항목으로 추정하는 스마트 파싱 로직이 있으며, 이를 메타데이터에 기록합니다.
- `public_data_client.py` — 금융위원회 공공데이터 API 기반; 과거 시가총액 조회 (재무정보 페이지 PER/PBR 계산용). LRU 캐시(maxsize=5000)를 통해 과거 데이터를 영구 캐싱합니다. 종목명 매핑이 필요하며, DB 조회로 자동 fallback합니다.
- `stock_client.py` — pykrx 기반; OHLCV + 펀더멘털 (PER, PBR, 배당수익률). 종목 검색 엔드포인트는 KOSPI/KOSDAQ 전체 종목 리스트를 메모리에 캐시합니다. **PER/PBR 계산에서는 금융위원회 API의 2차 fallback으로 사용됩니다.**
- `naver_client.py` — Naver 뉴스/블로그 검색 API.

**PER/PBR 계산 전략 (재무정보 페이지):**
재무정보 페이지에 표시되는 PER/PBR은 **과거 분기말/연말 시점**의 시가총액 기반입니다. 2단계 fallback 구조:
1. **1차: 금융위원회 공공데이터 API** — 필요한 날짜만 배치 조회 (예: 8개 분기의 종료일). 정부 공식 데이터로 법적으로 안전하며 D+1 데이터 제공. 캐싱으로 호출 제한 문제 없음.
2. **2차: pykrx fallback** — 금융위원회 API 실패 시 pykrx로 자동 전환. 범위 조회 방식이지만 휴장일 대응을 위해 전후 여유를 둡니다.

> 참고: 향후 **실시간 PER/PBR** (현재 시점 시가총액 기준)은 별도 페이지/기능으로 구현 예정이며, KIS API 또는 pykrx를 사용할 계획입니다. 재무정보 페이지는 역사적 데이터를 보여주는 것이 목적입니다.

**증분 데이터 수집 (`app/services/financial_service.py`):** 종목이 등록되거나 수동 갱신이 트리거될 때, 서비스는 DB에서 기존 `(fiscal_year, fiscal_quarter)` 쌍을 조회하고 누락된 기간만 DART에서 가져옵니다. 쓰기는 PostgreSQL `INSERT … ON CONFLICT DO UPDATE` (upsert)를 사용합니다. `force` 플래그는 기존 데이터 확인을 우회합니다.

**LangGraph 에이전트 파이프라인 (`app/agents/`):**
```
START → orchestrator_start
    ├── collect_information   (병렬)
    └── analyze_financials    (병렬)
    → orchestrator_merge
    → evaluate_valuation
    → generate_report → END
```
- `state.py`는 그래프를 관통하는 공유 `AnalysisState` TypedDict를 정의합니다.
- 각 에이전트 하위 디렉토리(`information/`, `financial/`, `valuation/`, `report/`)에는 `agent.py`(노드 함수), `prompts.py`, 그리고 선택적으로 `tools/` 패키지가 있습니다.
- 컴파일된 그래프 인스턴스는 `app/agents/graph.py`의 `analysis_graph`에 있습니다.
- LLM 호출은 `app/llm/provider.py`를 통과하며, **LiteLLM**을 사용합니다 — 이것이 OpenAI와 Anthropic 모델을 전환하는 단일 추상화 레이어입니다. 모델은 settings의 `default_llm_model`로 선택되거나 요청 시마다 오버라이드됩니다.

**Knowledge Base:** 프로젝트 루트의 `knowledge/` 디렉토리에 있는 마크다운 파일들(`deep_value.md`, `quality.md`)이 백엔드 컨테이너의 `/app/knowledge/`에 마운트됩니다. 가치평가 에이전트가 이 파일을 읽어 점수 로직의 기준으로 사용합니다.

**스케줄러 (`app/scheduler/`):** APScheduler 기반 백그라운드 작업 실행기입니다. `full` Docker Compose 프로파일을 사용할 때만 시작됩니다. 주기적 데이터 갱신을 위한 것으로, 아직 에이전트 파이프라인에 완전히 연결되지 않았습니다 (Phase 7 예정).

### 프론트엔드 (`frontend/`)

**프레임워크:** Next.js 16 App Router. Tailwind CSS 4로 스타일링. TypeScript strict 모드.

**페이지 구조는 백엔드 리소스와 대응됩니다:**
- `/` — 홈 페이지 (최근 보고서 + 통계)
- `/companies` — 페이지네이션된 목록, 검색, 종목 등록 모달
- `/companies/[stock_code]` — 종목 상세: 연간(6년) + 분기(8분기) 재무실적 테이블
- `/reports`, `/reports/[slug]` — 보고서 목록 및 상세
- `/admin` — 분석 실행을 트리거하는 대시보드
- `/api/revalidate` — 백엔드가 보고서를 생성한 후 호출하는 ISR 재검증 웹훅

**API 클라이언트:** `src/lib/api.ts`가 백엔드 호출의 단일 진입점입니다. 모든 요청에 `NEXT_PUBLIC_API_URL/api/v1` 접두사를 붙입니다. 모든 fetch 함수가 직접 내보내진 것에서, 래퍼 클래스나 컨텍스트 프로바이더는 없습니다.

**타입:** `src/lib/types.ts`에 모든 TypeScript 인터페이스와 UI 전반에 사용되는 verdict 레이블/색상 맵이 있습니다.

**경로 별칭:** `@/*`는 `src/*`에 매핑됩니다 (`tsconfig.json`에 설정).

### 환경 변수 및 비밀 정보

루트 `.env` 파일(gitignored)이 진실의 소스입니다. `env_file`을 통해 백엔드와 스케줄러 컨테이너에 전달됩니다. 프론트엔드는 `NEXT_PUBLIC_API_URL`만 필요하며 이것은 `docker-compose.yml`에서 설정됩니다. 프론트엔드 로컬 개발 시 `frontend/.env.local`에 해당 변수를 생성하세요.

### 주의해야 할 주요 설계 결정사항

1. **DB 세션 이중 패턴** — LangGraph 툴 내부에서 비동기 세션을, FastAPI 라우트 핸들러 내부에서 동기 세션을 사용하면 안 됩니다.
2. **매출액 추정 메타데이터** — `FinancialStatement.raw_data_json`에 `revenue`가 추정된 여부와 원본 계정과목명이 저장됩니다. 프론트엔드는 추정값에 별표와 툴팁을 표시합니다.
3. **Q4 = 연간** — 분기 수집 대상은 Q4를 명시적으로 제외합니다; 연간 데이터는 `report_type="annual"`로 별도 조회됩니다. `fiscal_quarter` 컬럼의 값은 연간 행에서도 `4`로 설정됩니다. Q4 단독 실적 자동 생성은 Q1, Q2, Q3가 모두 존재할 때만 수행됩니다.
4. **종목 검색 캐시** — `stocks.py`는 pykrx 종목 리스트를 모듈 레벨 변수로 캐시합니다. 백엜드 프로세스를 재시작하면 첫 번째 검색 요청이 들어올 때까지 캐시가 비어있습니다.
5. **ISR 재검증** — 백엔드는 보고서를 생성한 후 공유 비밀 키와 함께 `{FRONTEND_URL}/api/revalidate`에 POST합니다. 프론트엔드 라우트 핸들러는 해당 페이지에 대해 `revalidatePath`를 호출합니다.
6. **PER/PBR 계산 3단계 fallback** — 재무정보 페이지의 분기별 PER 계산은 (1) pykrx fundamentals trailing PER → (2) 시가총액 / (분기 순이익 × 4) → (3) PBR 역산 ((PBR × 자본총계) / (순이익 × 4)) 순서로 시도합니다. PBR 계산은 항상 시가총액 / 자본총계입니다. 연간 PER은 시가총액 / 연간 순이익으로 직접 계산합니다.
