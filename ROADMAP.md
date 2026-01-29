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

## Phase 2: 데이터 소스 & LLM 🚧 **다음 단계**

### 목표
외부 데이터를 가져오는 클라이언트와 LLM 연동 완성

### 구현 항목
- [ ] **DART 클라이언트** (`backend/app/data_sources/dart_client.py`)
  - OpenDartReader 래퍼 작성
  - 재무제표 조회 함수 (fnlttSinglAcntAll)
  - 공시 검색 함수
  - 삼성전자(005930) 테스트

- [ ] **주가 데이터 클라이언트** (`backend/app/data_sources/stock_client.py`)
  - pykrx 래퍼 작성
  - OHLCV 데이터 조회
  - 시가총액 조회
  - 테스트 스크립트

- [ ] **네이버 API 클라이언트** (`backend/app/data_sources/naver_client.py`)
  - 뉴스 검색 API (news.json)
  - 블로그 검색 API (blog.json)
  - 페이지네이션 처리
  - 테스트 스크립트

- [ ] **YouTube 클라이언트** (`backend/app/data_sources/youtube_client.py`)
  - YouTube Data API v3 연동
  - 영상 검색 및 메타데이터 조회
  - 테스트 스크립트

- [ ] **LiteLLM 프로바이더 설정**
  - OpenAI, Anthropic 설정
  - 폴백 체인 구성 (Claude 실패 시 GPT로)
  - 비용 추적 로깅

- [ ] **LangChain 도구 래핑**
  - 각 데이터 소스를 LangChain Tool로 변환
  - 도구 설명(description) 작성
  - 프롬프트 템플릿 작성

### 검증
```bash
# 삼성전자(005930) 데이터 조회 테스트
python backend/tests/test_dart_client.py
python backend/tests/test_stock_client.py

# LLM 연동 테스트
python backend/tests/test_llm_provider.py
```

---

## Phase 3: 에이전트 파이프라인 📋 **계획됨**

### 목표
4개 에이전트가 협력하는 LangGraph 파이프라인 완성 (프로젝트 핵심)

### 구현 항목
- [ ] **LangGraph 그래프 완성** (`backend/app/agents/graph.py`)
  - 병렬 실행 구조 (fan-out/fan-in) 구현
  - PostgreSQL 체크포인터 설정
  - 에러 핸들링 및 재시도 로직

- [ ] **정보 수집 에이전트** (`backend/app/agents/information/`)
  - agent.py: 메인 에이전트 로직
  - prompts.py: 시스템 프롬프트
  - tools/: DART, Naver, YouTube, 블로그 도구
  - 뉴스 센티먼트 분석
  - 실적 전망 요약

- [ ] **재무 분석 에이전트** (`backend/app/agents/financial/`)
  - agent.py: 재무 분석 로직
  - prompts.py: 분석 프롬프트
  - tools/: DART 재무, 주가, 비율 계산
  - 재무비율 자동 계산 (PER, PBR, ROE, NCAV, 그레이엄 넘버 등)
  - 동종업계 비교

- [ ] **가치투자 평가 에이전트** (`backend/app/agents/valuation/`)
  - **핵심**: knowledge/*.md 파일 로딩 구현
  - Deep Value 평가 (정량 기준)
  - Quality 평가 (정성 + 정량)
  - frameworks/deep_value.py: 정량 계산 함수
  - frameworks/quality.py: 정성 평가 로직
  - 각 프레임워크별 점수 산출 (0-100)

- [ ] **보고서 생성 에이전트** (`backend/app/agents/report/`)
  - 모든 분석 결과 종합
  - 마크다운 형식 보고서 생성
  - DB 저장 (analysis_reports 테이블)
  - Slug 생성 (URL용)

- [ ] **analysis_service.py 구현**
  - FastAPI에서 LangGraph 파이프라인 호출
  - 백그라운드 작업 실행
  - 상태 업데이트 (pending → completed)

### 검증
```bash
# 3~5개 기업 E2E 테스트
python backend/tests/test_pipeline_e2e.py --companies 005930,035420,035720

# analysis_runs 테이블에서 상태 확인
psql -d agent_vi -c "SELECT id, status, company_id FROM analysis_runs ORDER BY created_at DESC LIMIT 5;"
```

---

## Phase 4: API & 프론트엔드 📋 **계획됨**

### 목표
분석 결과를 웹에서 보여주는 UI 완성

### 구현 항목
- [ ] **분석 실행 API 완성**
  - `/api/v1/analysis/run` 백그라운드 실행
  - 실시간 상태 조회
  - WebSocket 또는 폴링 방식 선택

- [ ] **Next.js 페이지 구현**
  - 홈: 최근 보고서 + 요약 통계
  - 보고서 목록: 필터/정렬 (시장, 평가 등)
  - 보고서 상세: 전체 분석 내용
  - 기업 상세: 과거 보고서 이력

- [ ] **데이터 시각화**
  - Recharts 라이브러리 추가
  - 재무 트렌드 차트 (매출, 이익)
  - **밸류에이션 레이더 차트** (Deep Value vs Quality)
  - 뉴스 센티먼트 타임라인
  - 주가 차트

- [ ] **ISR 재검증 웹훅**
  - 백엔드: 보고서 발행 시 프론트엔드 호출
  - 프론트엔드: `/api/revalidate` 구현
  - 자동 페이지 갱신 확인

- [ ] **반응형 디자인**
  - 모바일/태블릿 대응
  - 다크 모드 (선택 사항)

### 검증
```bash
# 프론트엔드 빌드
cd frontend && npm run build

# 보고서 페이지 확인
# http://localhost:3000/reports/{slug}
```

---

## Phase 5: 스케줄링 & 관리자 📋 **계획됨**

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

| Phase | 예상 기간 | 상태 |
|-------|----------|------|
| Phase 1 | 1주 | ✅ 완료 |
| Phase 2 | 1-2주 | 🚧 진행 예정 |
| Phase 3 | 2-3주 | 📋 계획됨 |
| Phase 4 | 2주 | 📋 계획됨 |
| Phase 5 | 1주 | 📋 계획됨 |
| Phase 6 | 1주 | 📋 계획됨 |

**전체 예상 기간**: 8-11주

---

## 핵심 구현 파일 우선순위

구현 시 우선적으로 확인해야 할 파일:

1. **Phase 2**: `backend/app/data_sources/dart_client.py`
2. **Phase 3**: `backend/app/agents/graph.py` (파이프라인의 핵심)
3. **Phase 3**: `backend/app/agents/valuation/agent.py` (knowledge 로딩)
4. **Phase 4**: `frontend/src/app/reports/[slug]/page.tsx` (최종 산출물)
5. **Phase 5**: `backend/app/scheduler/jobs.py` (자동화)

---

## 참고 문서

- [아키텍처 문서](./docs/architecture.md) - 시스템 설계 상세
- [계획서](/.claude/plans/sprightly-jumping-firefly.md) - 초기 설계 문서
- README.md - 프로젝트 소개 및 빠른 시작
