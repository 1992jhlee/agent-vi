# Agent-VI 구현 로드맵

## 전체 개요

Agent-VI는 6단계(Phase)로 나뉘어 구현됩니다. 각 단계는 독립적으로 테스트 가능하며, 점진적으로 기능을 확장합니다.

---

## Phase 1: 프로젝트 기반 구축 ✅ **완료**

### 목표
프로젝트 골격과 데이터베이스 설계 완성

### 완료 항목
- [x] Python 프로젝트 초기화 (pyproject.toml)
- [x] Next.js 15 프로젝트 초기화 (TypeScript + Tailwind)
- [x] Docker Compose 설정 (PostgreSQL + backend + frontend)
- [x] SQLAlchemy 2.0 모델 7개 작성
  - companies, analysis_runs, financial_statements
  - stock_prices, news_articles, valuation_metrics, analysis_reports
- [x] Alembic 마이그레이션 설정
- [x] FastAPI 기본 골격
  - config.py (pydantic-settings)
  - 5개 API 라우터 (companies, reports, analysis, financials, health)
- [x] Next.js 페이지 골격 (7개 페이지)
- [x] Knowledge Base 마크다운 파일 (deep_value.md, quality.md)
- [x] LangGraph 상태 스키마 및 그래프 골격
- [x] 문서 작성 (README.md, docs/architecture.md)

### 검증
```bash
# 프로젝트 구조 확인
ls backend/app/db/models/
ls frontend/src/app/

# API 문서 확인 (서버 실행 후)
# http://localhost:8000/docs
```

---

## Phase 2: 데이터 소스 & LLM ✅ **완료**

### 목표
외부 데이터를 가져오는 클라이언트와 LLM 연동 완성

### 완료 항목
- [x] **DART 클라이언트** (`backend/app/data_sources/dart_client.py`)
  - OpenDartReader 래퍼 작성
  - 재무제표 조회 함수 (fnlttSinglAcntAll)
  - 공시 검색 함수
  - 에러 핸들링 및 재시도 로직

- [x] **주가 데이터 클라이언트** (`backend/app/data_sources/stock_client.py`)
  - pykrx 래퍼 작성
  - OHLCV 데이터 조회
  - 시가총액, 52주 최고/최저가 조회
  - 수익률 계산 (1M, 3M, 6M, 1Y)

- [x] **네이버 API 클라이언트** (`backend/app/data_sources/naver_client.py`)
  - 뉴스/블로그 검색 API (비동기)
  - 페이지네이션 및 Rate limiting 처리
  - HTML 태그 제거

- [ ] **YouTube 클라이언트** - Deferred (나중에 진행)

- [x] **LiteLLM 프로바이더 설정**
  - OpenAI, Anthropic 설정
  - 폴백 체인 구성
  - 비용 추적 로깅

- [x] **LangChain 도구 래핑**
  - DART, Naver, 주가 분석 도구 구현

### 검증
```bash
# 삼성전자(005930) 데이터 조회 테스트
python backend/tests/test_dart_client.py
python backend/tests/test_stock_client.py

# LLM 연동 테스트
python backend/tests/test_llm_provider.py
```

---

## Phase 3: 에이전트 파이프라인 ✅ **완료**

### 목표
4개 에이전트가 협력하는 LangGraph 파이프라인 완성 (프로젝트 핵심)

### 완료 항목
- [x] **LangGraph 그래프 완성** (`backend/app/agents/graph.py`)
  - 병렬 실행 구조 (fan-out/fan-in) 구현
  - 에러 핸들링
  - [ ] PostgreSQL 체크포인터 설정 (Optional)

- [x] **정보 수집 에이전트** (`backend/app/agents/information/`)
  - agent.py: 메인 에이전트 로직
  - prompts.py: 시스템 프롬프트
  - tools/: DART 공시, Naver 뉴스 검색
  - LLM 기반 정보 종합 분석

- [x] **재무 분석 에이전트** (`backend/app/agents/financial/`)
  - agent.py: 재무 분석 로직
  - prompts.py: 분석 프롬프트
  - tools/: DART 재무, 주가 분석
  - 재무비율 자동 계산 (ROE, 영업이익률, 부채비율)

- [x] **가치투자 평가 에이전트** (`backend/app/agents/valuation/`)
  - knowledge/*.md 파일 로딩 구현
  - Deep Value 평가 (0-100 점수)
  - Quality 평가 (0-100 점수)
  - 투자 판단 (strong_buy/buy/hold/sell/strong_sell)

- [x] **보고서 생성 에이전트** (`backend/app/agents/report/`)
  - 모든 분석 결과 종합
  - 마크다운 형식 보고서 생성
  - DB 저장 (analysis_reports 테이블)
  - Slug 생성 (python-slugify)
  - ISR 재검증 웹훅 호출

- [x] **analysis_service.py 구현**
  - LangGraph 파이프라인 호출
  - ThreadPoolExecutor 백그라운드 실행
  - 상태 업데이트 (pending → running → completed/failed)

### 검증
```bash
# E2E 테스트
python backend/tests/test_pipeline_e2e.py

# analysis_runs 테이블에서 상태 확인
psql -d agent_vi -c "SELECT id, status, company_id FROM analysis_runs ORDER BY created_at DESC LIMIT 5;"
```

---

## Phase 4: API & 프론트엔드 ✅ **완료**

### 목표
분석 결과를 웹에서 보여주는 UI 완성

### 완료 항목
- [x] **분석 실행 API 완성**
  - `/api/v1/analysis/run` 백그라운드 실행 (ThreadPoolExecutor)
  - 실시간 상태 조회 (폴링 방식)
  - 에러 처리

- [x] **Next.js 페이지 구현**
  - 홈: 최근 보고서 + 요약 통계
  - 보고서 목록: 필터/정렬
  - 보고서 상세: 전체 분석 내용, Deep Value/Quality 점수 표시
  - 기업 관리: CRUD, 검색, 필터링
  - 관리자 대시보드: 분석 실행 UI, 실시간 상태 폴링

- [x] **ISR 재검증 웹훅**
  - 백엔드: 보고서 발행 시 프론트엔드 호출
  - 프론트엔드: `/api/revalidate` 구현
  - Secret 토큰 검증

- [ ] **데이터 시각화** - Phase 5로 이동
  - Recharts 차트
  - 밸류에이션 레이더 차트

- [ ] **반응형 디자인** - Phase 6로 이동
  - 모바일/태블릿 대응
  - 다크 모드

### 검증
```bash
# 프론트엔드 빌드
cd frontend && npm run build

# 보고서 페이지 확인
# http://localhost:3000/reports/{slug}
```

---

## Phase 5: 스케줄링 & 관리자 🚧 **다음 단계**

### 목표
자동화 및 운영 도구 완성

### 구현 항목
- [ ] **APScheduler 작업 정의** (`backend/app/scheduler/jobs.py`)
  - 일일 주가 업데이트 (평일 18:00 KST)
  - 일일 뉴스 스캔 (평일 08:00, 14:00 KST)
  - 주간 전체 분석 (토요일 09:00 KST)
  - 분기 재무 업데이트 (1/4/7/10월 15일)

- [ ] **스케줄러 프로세스 분리**
  - `backend/app/scheduler/run.py` 완성
  - Docker Compose profile 설정
  - 다중 워커 동시 실행 방지

- [ ] **관리자 대시보드** (`frontend/src/app/admin/`)
  - 분석 실행 모니터링
  - 수동 분석 트리거
  - 진행 중인 작업 상태 표시
  - 에러 로그 조회

- [ ] **투자 철학 편집 UI** (`frontend/src/app/admin/knowledge/`)
  - 마크다운 에디터 통합 (react-markdown-editor)
  - 백엔드 API: `GET/PUT /api/v1/admin/knowledge/{filename}`
  - 실시간 미리보기
  - 변경 이력 (Git 연동 선택 사항)

### 검증
```bash
# 스케줄러 단독 실행
docker compose --profile full up scheduler

# 스케줄 작업 확인
docker compose logs scheduler | grep "Executing job"
```

---

## Phase 6: 배포 📋 **계획됨**

### 목표
프로덕션 환경 배포 및 모니터링

### 구현 항목
- [ ] **백엔드 배포**
  - Koyeb / Railway / Fly.io 선택
  - 환경 변수 설정
  - 도메인 연결

- [ ] **프론트엔드 배포**
  - Vercel 배포
  - 환경 변수 설정 (NEXT_PUBLIC_API_URL)
  - 도메인 연결

- [ ] **데이터베이스**
  - Neon / Supabase Managed PostgreSQL
  - 백업 설정
  - 마이그레이션 실행

- [ ] **에러 모니터링**
  - Sentry 연동
  - 알림 설정
  - 에러 대시보드

- [ ] **로깅**
  - 구조화된 JSON 로그
  - 로그 레벨 설정
  - 로그 보관 정책

- [ ] **성능 최적화**
  - DB 인덱스 최적화
  - API 응답 캐싱
  - CDN 설정 (프론트엔드)

### 검증
```bash
# 프로덕션 헬스 체크
curl https://api.agent-vi.com/api/v1/health

# 프론트엔드 접속
# https://agent-vi.com
```

---

## 마일스톤

| Phase | 설명 | 상태 |
|-------|------|------|
| Phase 1 | 프로젝트 기반 구축 | ✅ 완료 |
| Phase 2 | 데이터 소스 & LLM | ✅ 완료 |
| Phase 3 | 에이전트 파이프라인 | ✅ 완료 |
| Phase 4 | API & 프론트엔드 | ✅ 완료 |
| Phase 5 | 스케줄링 & 관리자 | 🚧 다음 단계 |
| Phase 6 | 배포 | 📋 계획됨 |

**진행률**: 약 85% (Phase 1~4 완료)

---

## 핵심 구현 파일 우선순위

### 완료된 핵심 파일
- ✅ `backend/app/data_sources/dart_client.py` - DART 재무 데이터
- ✅ `backend/app/agents/graph.py` - LangGraph 파이프라인 핵심
- ✅ `backend/app/agents/valuation/agent.py` - knowledge base 로딩
- ✅ `frontend/src/app/reports/[slug]/page.tsx` - 보고서 상세 페이지
- ✅ `backend/app/services/analysis_service.py` - 분석 서비스

### 다음 구현 파일
- 📋 `backend/app/scheduler/jobs.py` - 스케줄링 작업 정의
- 📋 `backend/app/api/v1/admin.py` - 관리자 API (knowledge 편집)

---

## 참고 문서

- [아키텍처 문서](./docs/architecture.md) - 시스템 설계 상세
- [계획서](/.claude/plans/sprightly-jumping-firefly.md) - 초기 설계 문서
- README.md - 프로젝트 소개 및 빠른 시작
