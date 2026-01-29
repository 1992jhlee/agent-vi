# TODO

## 🚀 현재 작업: Phase 2 준비 중

---

## Phase 1: 프로젝트 기반 구축 ✅

### 프로젝트 구조
- [x] Python 프로젝트 초기화 (pyproject.toml)
- [x] Next.js 15 초기화 (TypeScript + Tailwind)
- [x] Docker Compose 설정 (db + backend + frontend)
- [x] .gitignore, .env.example 작성
- [x] 디렉토리 구조 생성

### 백엔드
- [x] SQLAlchemy 모델 7개 작성
  - [x] companies
  - [x] analysis_runs
  - [x] financial_statements
  - [x] stock_prices
  - [x] news_articles
  - [x] valuation_metrics
  - [x] analysis_reports
- [x] Alembic 마이그레이션 설정 (env.py, alembic.ini)
- [x] FastAPI 기본 골격
  - [x] config.py (pydantic-settings)
  - [x] main.py (CORS, lifespan)
  - [x] db/session.py (async session)
- [x] API 라우터 5개
  - [x] /api/v1/health
  - [x] /api/v1/companies (CRUD)
  - [x] /api/v1/reports (목록, 상세)
  - [x] /api/v1/analysis (실행, 상태)
  - [x] /api/v1/financials (재무제표, 지표)
- [x] Pydantic 스키마 작성
- [x] LangGraph 골격 (state.py, graph.py)
- [x] LLM provider.py 골격

### 프론트엔드
- [x] Next.js 페이지 7개 골격
  - [x] / (홈)
  - [x] /reports (보고서 목록)
  - [x] /reports/[slug] (보고서 상세)
  - [x] /companies (기업 목록)
  - [x] /admin (관리자 대시보드)
  - [x] /admin/knowledge (투자 철학 편집)
  - [x] /api/revalidate (ISR 웹훅)
- [x] lib/api.ts (백엔드 API 클라이언트)
- [x] lib/types.ts (TypeScript 타입 정의)
- [x] Layout (헤더, 푸터, 네비게이션)

### Knowledge Base
- [x] knowledge/deep_value.md 작성
- [x] knowledge/quality.md 작성

### 문서
- [x] README.md
- [x] docs/architecture.md
- [x] ROADMAP.md

---

## Phase 2: 데이터 소스 & LLM 🚧

### 환경 설정
- [x] .env 파일 생성 및 API 키 입력
  - [x] DART_API_KEY
  - [x] NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
  - [ ] YOUTUBE_API_KEY (나중에 진행)
  - [x] OPENAI_API_KEY
- [ ] Alembic 초기 마이그레이션 생성 및 적용
  ```bash
  cd backend
  alembic revision --autogenerate -m "Initial schema"
  alembic upgrade head
  ```
  > **Note**: Docker 환경 설정 후 진행 필요

### 데이터 소스 클라이언트
- [x] **DART 클라이언트** (backend/app/data_sources/dart_client.py)
  - [x] OpenDartReader 래퍼 클래스 작성
  - [x] 재무제표 조회 함수 (fnlttSinglAcntAll)
  - [x] 공시 검색 함수 (list)
  - [x] 에러 핸들링 및 재시도 로직
  - [x] 기업코드 조회 함수 (종목코드 → DART 기업코드)
  - [x] 재무 데이터 파싱 함수

- [x] **주가 데이터 클라이언트** (backend/app/data_sources/stock_client.py)
  - [x] pykrx 래퍼 클래스 작성
  - [x] OHLCV 데이터 조회 (get_market_ohlcv_by_date)
  - [x] 시가총액 조회 (get_market_cap)
  - [x] 날짜 범위 처리
  - [x] 최근 주가 조회 함수
  - [x] 펀더멘털 데이터 조회 (PER, PBR, 배당수익률)
  - [x] 수익률 계산 함수 (1M, 3M, 6M, 1Y)
  - [x] 52주 최고/최저가 조회

- [x] **네이버 API 클라이언트** (backend/app/data_sources/naver_client.py)
  - [x] httpx 기반 비동기 클라이언트 작성
  - [x] 뉴스 검색 API (news.json)
  - [x] 블로그 검색 API (blog.json)
  - [x] 동시 검색 함수 (뉴스 + 블로그)
  - [x] 페이지네이션 처리
  - [x] Rate limiting 처리 (delay 파라미터)
  - [x] HTML 태그 제거 함수

- [ ] **YouTube 클라이언트** (backend/app/data_sources/youtube_client.py)
  - [ ] YouTube Data API v3 연동
  - [ ] 영상 검색 (search.list)
  - [ ] 메타데이터 조회 (videos.list)
  - [ ] 할당량 관리
  > **Deferred**: 유저 요청으로 나중에 진행

### LLM 설정
- [x] LiteLLM 프로바이더 설정 완성 (backend/app/llm/provider.py)
  - [x] OpenAI 설정
  - [x] Anthropic 설정 (ANTHROPIC_API_KEY 미설정 시 GPT만 사용)
  - [x] 폴백 체인 구성 (Claude 실패 시 GPT로, 또는 그 반대)
  - [x] 비용 추적 로깅 (usage 정보)
  - [x] 동기/비동기 completion 메서드
  - [x] 싱글톤 패턴 (get_llm_provider)

### LangChain 도구 래핑
- [ ] information/tools/dart_tool.py
- [ ] information/tools/naver_news_tool.py
- [ ] information/tools/youtube_tool.py
- [ ] information/tools/blog_search_tool.py
- [ ] financial/tools/dart_financial_tool.py
- [ ] financial/tools/stock_price_tool.py
- [ ] financial/tools/ratio_calculator.py

### 테스트 스크립트
- [x] tests/test_dart_client.py
- [x] tests/test_stock_client.py
- [x] tests/test_naver_client.py
- [ ] tests/test_youtube_client.py (Deferred)
- [x] tests/test_llm_provider.py

---

## Phase 3: 에이전트 파이프라인 📋

### LangGraph 그래프
- [ ] graph.py 완성
  - [ ] 병렬 실행 구조 (fan-out/fan-in)
  - [ ] PostgreSQL 체크포인터 설정
  - [ ] 에러 핸들링
  - [ ] 재시도 로직

### 정보 수집 에이전트
- [ ] agents/information/agent.py
- [ ] agents/information/prompts.py
- [ ] 뉴스 센티먼트 분석
- [ ] 실적 전망 요약

### 재무 분석 에이전트
- [ ] agents/financial/agent.py
- [ ] agents/financial/prompts.py
- [ ] 재무비율 자동 계산 로직
- [ ] 동종업계 비교

### 가치투자 평가 에이전트
- [ ] agents/valuation/agent.py
  - [ ] knowledge/*.md 파일 로딩 구현
  - [ ] Deep Value 평가
  - [ ] Quality 평가
- [ ] agents/valuation/prompts.py
- [ ] frameworks/deep_value.py (정량 계산)
- [ ] frameworks/quality.py (정성 평가)

### 보고서 생성 에이전트
- [ ] agents/report/agent.py
- [ ] agents/report/templates.py
- [ ] 마크다운 보고서 생성
- [ ] DB 저장 로직
- [ ] Slug 생성

### 서비스 레이어
- [ ] services/analysis_service.py
  - [ ] LangGraph 파이프라인 호출
  - [ ] 백그라운드 작업 실행
  - [ ] 상태 업데이트

### E2E 테스트
- [ ] tests/test_pipeline_e2e.py
- [ ] 3~5개 기업으로 전체 파이프라인 테스트

---

## Phase 4: API & 프론트엔드 📋

### 분석 실행 API
- [ ] api/v1/analysis.py 완성
  - [ ] 백그라운드 실행
  - [ ] 실시간 상태 조회
  - [ ] 에러 처리

### Next.js 페이지 구현
- [ ] 홈 페이지 (최근 보고서 + 통계)
- [ ] 보고서 목록 (필터/정렬)
- [ ] 보고서 상세 (전체 분석 내용)
- [ ] 기업 상세 (보고서 이력)

### 데이터 시각화
- [ ] Recharts 라이브러리 추가
- [ ] 재무 트렌드 차트
- [ ] 밸류에이션 레이더 차트 (Deep Value vs Quality)
- [ ] 뉴스 센티먼트 타임라인
- [ ] 주가 차트

### ISR 재검증
- [ ] 백엔드: 보고서 발행 시 웹훅 호출
- [ ] 프론트엔드: /api/revalidate 완성
- [ ] 자동 갱신 테스트

### 반응형 디자인
- [ ] 모바일/태블릿 대응
- [ ] 다크 모드 (선택 사항)

---

## Phase 5: 스케줄링 & 관리자 📋

### APScheduler
- [ ] scheduler/jobs.py 작업 정의
  - [ ] 일일 주가 업데이트
  - [ ] 일일 뉴스 스캔
  - [ ] 주간 전체 분석
  - [ ] 분기 재무 업데이트
- [ ] scheduler/run.py 완성
- [ ] Docker Compose profile 설정

### 관리자 대시보드
- [ ] admin/ 분석 실행 모니터링
- [ ] 수동 분석 트리거
- [ ] 진행 중인 작업 상태
- [ ] 에러 로그 조회

### 투자 철학 편집 UI
- [ ] admin/knowledge/ 마크다운 에디터
- [ ] 백엔드 API: GET/PUT /api/v1/admin/knowledge/{filename}
- [ ] 실시간 미리보기
- [ ] 변경 이력 (선택 사항)

---

## Phase 6: 배포 📋

### 백엔드 배포
- [ ] Koyeb / Railway / Fly.io 선택
- [ ] 환경 변수 설정
- [ ] 도메인 연결

### 프론트엔드 배포
- [ ] Vercel 배포
- [ ] 환경 변수 설정
- [ ] 도메인 연결

### 데이터베이스
- [ ] Neon / Supabase 선택
- [ ] 백업 설정
- [ ] 마이그레이션 실행

### 모니터링
- [ ] Sentry 연동
- [ ] 로깅 시스템
- [ ] 알림 설정

### 성능 최적화
- [ ] DB 인덱스 최적화
- [ ] API 응답 캐싱
- [ ] CDN 설정

---

## 📝 메모

### 막혔던 부분
-

### 해결 방법
-

### 다음 세션 시작할 때
1. TODO.md 확인
2. Phase 2 첫 항목부터 시작: .env 파일 설정
3. DART 클라이언트 구현

---

## 참고

- [ROADMAP.md](./ROADMAP.md) - 전체 로드맵
- [docs/architecture.md](./docs/architecture.md) - 아키텍처 설계
- [계획서](/.claude/plans/sprightly-jumping-firefly.md) - 초기 설계
