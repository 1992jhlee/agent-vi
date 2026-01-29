# Agent-VI 아키텍처 문서

## 개요

Agent-VI는 가치투자 철학을 기반으로 한국 주식(KOSPI/KOSDAQ) 기업을 분석하고 보고서를 생성하는 멀티 에이전트 시스템입니다.

### 핵심 특징

- **투자 철학**: Deep Value(자산가치 중심) + Quality(기업 품질 중심) 이원화
- **에이전트 프레임워크**: LangGraph (상태 그래프 기반 워크플로우)
- **병렬 실행**: 정보 수집과 재무 분석을 동시에 진행
- **지식 기반**: 사용자가 직접 편집 가능한 마크다운 파일로 투자 철학 관리

## 기술 스택

| 영역 | 기술 |
|------|------|
| 에이전트 | LangGraph 1.0+ (PostgreSQL 체크포인팅) |
| LLM | LiteLLM 1.50+ (OpenAI/Anthropic 멀티 프로바이더) |
| 백엔드 | FastAPI 0.115+ + SQLAlchemy 2.0 + Alembic |
| 프론트엔드 | Next.js 15 (App Router, ISR) + Tailwind CSS |
| 데이터베이스 | PostgreSQL 16 |
| 스케줄러 | APScheduler 3.10+ (별도 프로세스) |
| 데이터 소스 | OpenDartReader, pykrx, Naver API, YouTube Data API |

## 에이전트 파이프라인

```
[트리거: 수동 API 호출 또는 스케줄]
              |
    ┌─────────────────────┐
    │   Orchestrator       │ -- analysis_run 레코드 생성, 입력 검증
    └──────────┬──────────┘
         ┌─────┴─────┐        (병렬 실행)
         v           v
┌────────────────┐ ┌────────────────┐
│ 정보 수집       │ │ 재무 분석       │
│ Agent          │ │ Agent          │
│ - DART 공시    │ │ - 재무제표     │
│ - 네이버 뉴스  │ │ - 주가 데이터  │
│ - YouTube      │ │ - 재무비율     │
│ - 블로그       │ │ - 동종업계 비교│
└───────┬────────┘ └───────┬────────┘
        └────────┬─────────┘   (합류)
                 v
       ┌──────────────────┐
       │ Orchestrator      │ -- 병렬 결과 검증 및 병합
       └────────┬─────────┘
                v
       ┌──────────────────┐
       │ 가치투자 평가     │ -- knowledge/*.md 로딩
       │ Agent            │ -- Deep Value + Quality 평가
       └────────┬─────────┘
                v
       ┌──────────────────┐
       │ 보고서 생성       │ -- 최종 보고서 작성 + DB 저장
       │ Agent            │ -- Next.js ISR 갱신 트리거
       └──────────────────┘
```

### LangGraph 선택 이유

1. **그래프 기반 DAG**: 정보수집/재무분석을 병렬 실행 (fan-out/fan-in)
2. **PostgreSQL 체크포인팅**: 실패 시 마지막 성공 노드부터 재개
3. **FastAPI 통합**: 일반 Python 라이브러리로 자연스럽게 통합
4. **확장성**: 새 에이전트 추가 = 노드 + 엣지 추가

## 투자 철학 Knowledge Base

### 구조

```
knowledge/
├── deep_value.md      # 자산가치 중심 투자 원칙
└── quality.md         # 기업 품질/성장 중심 투자 원칙
```

### 작동 원리

1. 에이전트가 분석 시 `knowledge/*.md` 파일을 로드
2. 파일 내용을 프롬프트에 직접 삽입하여 LLM에 전달
3. 사용자가 파일을 수정하면 **다음 분석부터 자동 반영**
4. 특정 대가 이름에 종속되지 않아 자유롭게 발전 가능

### 관리 UI

- `/admin/knowledge` 페이지에서 마크다운 에디터로 편집
- 백엔드 API: `GET/PUT /api/v1/admin/knowledge/{filename}`
- Git 커밋으로 변경 이력 추적 (선택 사항)

## 데이터베이스 스키마

### 핵심 테이블

#### companies
기업 기본 정보 및 관심 종목 관리

```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) UNIQUE NOT NULL,      -- "005930"
    company_name VARCHAR(200) NOT NULL,          -- "삼성전자"
    company_name_en VARCHAR(200),
    corp_code VARCHAR(20) UNIQUE,                -- DART 기업코드
    market VARCHAR(10) NOT NULL,                 -- KOSPI | KOSDAQ
    sector VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_companies_stock_code ON companies(stock_code);
CREATE INDEX idx_companies_market ON companies(market, is_active);
```

#### analysis_runs
분석 실행 추적

```sql
CREATE TABLE analysis_runs (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    status VARCHAR(20) NOT NULL,  -- pending|collecting|analyzing|evaluating|generating|completed|failed
    trigger_type VARCHAR(20),     -- manual|scheduled
    llm_model VARCHAR(100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_analysis_runs_status ON analysis_runs(status, created_at DESC);
```

#### financial_statements
DART 재무제표 데이터

```sql
CREATE TABLE financial_statements (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER NOT NULL,     -- 1,2,3,4 (4=연간)
    report_type VARCHAR(20) NOT NULL,    -- annual|quarterly
    revenue BIGINT,
    operating_income BIGINT,
    net_income BIGINT,
    total_assets BIGINT,
    total_liabilities BIGINT,
    total_equity BIGINT,
    operating_cash_flow BIGINT,
    investing_cash_flow BIGINT,
    financing_cash_flow BIGINT,
    dividends_paid BIGINT,
    shares_outstanding BIGINT,
    raw_data_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, fiscal_year, fiscal_quarter)
);
CREATE INDEX idx_financial_company_year ON financial_statements(company_id, fiscal_year DESC);
```

#### stock_prices
주가 데이터 (pykrx)

```sql
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    trade_date DATE NOT NULL,
    open_price INTEGER,
    high_price INTEGER,
    low_price INTEGER,
    close_price INTEGER,
    volume BIGINT,
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, trade_date)
);
CREATE INDEX idx_stock_prices_company_date ON stock_prices(company_id, trade_date DESC);
```

#### news_articles
수집된 뉴스/콘텐츠

```sql
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    analysis_run_id INTEGER REFERENCES analysis_runs(id),
    source_type VARCHAR(20),              -- naver_news|youtube|blog|dart_disclosure
    source_url TEXT,
    title VARCHAR(500),
    content_summary TEXT,
    published_at TIMESTAMP,
    sentiment_score FLOAT,                -- -1.0 ~ 1.0
    sentiment_label VARCHAR(20),          -- positive|negative|neutral
    relevance_score FLOAT,                -- 0.0 ~ 1.0
    raw_content TEXT,
    metadata_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_news_company_source ON news_articles(company_id, source_type, published_at DESC);
```

#### valuation_metrics
계산된 밸류에이션 지표

```sql
CREATE TABLE valuation_metrics (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    analysis_run_id INTEGER REFERENCES analysis_runs(id),
    metric_date DATE NOT NULL,
    -- Price Multiples
    per FLOAT, pbr FLOAT, psr FLOAT, pcr FLOAT, ev_ebitda FLOAT,
    -- Profitability
    roe FLOAT, roa FLOAT, operating_margin FLOAT, net_margin FLOAT,
    -- Safety
    debt_to_equity FLOAT, current_ratio FLOAT, interest_coverage FLOAT,
    -- Growth
    revenue_growth_yoy FLOAT, earnings_growth_yoy FLOAT, book_value_growth_yoy FLOAT,
    -- Dividends
    dividend_yield FLOAT, dividend_payout_ratio FLOAT,
    -- Deep Value Metrics
    ncav_per_share FLOAT, graham_number FLOAT, margin_of_safety_pct FLOAT,
    -- Quality Metrics
    owner_earnings BIGINT, moat_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### analysis_reports
최종 분석 보고서

```sql
CREATE TABLE analysis_reports (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    analysis_run_id INTEGER REFERENCES analysis_runs(id) UNIQUE,
    slug VARCHAR(200) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    report_date DATE NOT NULL,
    -- 섹션 (Markdown)
    executive_summary TEXT,
    company_overview TEXT,
    financial_analysis TEXT,
    news_sentiment_summary TEXT,
    earnings_outlook TEXT,
    -- 평가 (JSONB)
    deep_value_evaluation JSONB,         -- {score, analysis, signals}
    quality_evaluation JSONB,            -- {score, analysis, signals}
    -- 종합
    overall_score FLOAT,                 -- 0-100
    overall_verdict VARCHAR(20),         -- strong_buy|buy|hold|sell|strong_sell
    is_published BOOLEAN DEFAULT false,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_reports_published ON analysis_reports(is_published, report_date DESC);
CREATE INDEX idx_reports_slug ON analysis_reports(slug);
```

## API 엔드포인트

### 기업 관리

```
GET    /api/v1/companies                 # 기업 목록 (필터: market, sector, is_active, q)
POST   /api/v1/companies                 # 기업 등록
GET    /api/v1/companies/{stock_code}     # 기업 상세
PUT    /api/v1/companies/{stock_code}     # 기업 수정
DELETE /api/v1/companies/{stock_code}     # 기업 삭제
```

### 분석 관리

```
POST   /api/v1/analysis/run              # 분석 실행 트리거
GET    /api/v1/analysis/runs             # 분석 실행 목록
GET    /api/v1/analysis/runs/{run_id}    # 분석 실행 상태
POST   /api/v1/analysis/batch            # 배치 분석 트리거
```

### 보고서 (공개)

```
GET    /api/v1/reports                   # 보고서 목록 (필터: market, verdict)
GET    /api/v1/reports/latest            # 최근 보고서
GET    /api/v1/reports/{slug}            # 보고서 상세
GET    /api/v1/reports/company/{stock_code}  # 기업별 보고서
```

### 재무 데이터

```
GET    /api/v1/financials/{stock_code}           # 재무제표
GET    /api/v1/financials/{stock_code}/metrics   # 밸류에이션 지표
```

### 시스템

```
GET    /api/v1/health                    # 헬스 체크
```

## 프론트엔드 구조

### 페이지 (Next.js App Router)

| 경로 | 페이지 | 렌더링 | 설명 |
|------|------|--------|------|
| `/` | 홈 | ISR (60s) | 최근 보고서 + 요약 통계 |
| `/reports` | 보고서 목록 | ISR (60s) | 필터/정렬 가능 |
| `/reports/[slug]` | 보고서 상세 | ISR (on-demand) | 전체 분석 보고서 |
| `/companies` | 기업 목록 | SSR | 관심 종목 관리 |
| `/companies/[ticker]` | 기업 상세 | SSR | 기업 프로필 + 보고서 이력 |
| `/admin` | 관리자 대시보드 | CSR | 분석 실행 상태 |
| `/admin/knowledge` | 투자 철학 편집 | CSR | 마크다운 에디터 |

### ISR 재검증 웹훅

```
[Backend: 보고서 발행]
    |
    v
POST {FRONTEND_URL}/api/revalidate
    {
      "secret": "...",
      "slug": "report-slug"
    }
    |
    v
[Next.js: /reports/[slug] 재검증]
```

## 스케줄 전략

| 작업 | 주기 | 설명 |
|------|------|------|
| 일일 주가 업데이트 | 평일 18:00 KST | pykrx로 종가 수집 |
| 일일 뉴스 스캔 | 평일 08:00, 14:00 KST | 간략 뉴스 수집 (전체 분석 X) |
| 주간 전체 분석 | 매주 토요일 09:00 KST | 활성 기업 전체 분석 파이프라인 |
| 분기 재무 업데이트 | 1/4/7/10월 15일 | 실적 시즌 후 재무제표 갱신 |

## 배포 전략

### 로컬 개발

```bash
# 1. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력

# 2. Docker Compose로 전체 스택 실행
docker compose up

# 백엔드: http://localhost:8000
# API 문서: http://localhost:8000/docs
# 프론트엔드: http://localhost:3000
```

### 프로덕션 배포

- **백엔드**: Koyeb / Railway / Fly.io
- **프론트엔드**: Vercel (Next.js 최적화)
- **데이터베이스**: Neon / Supabase (Managed PostgreSQL)
- **스케줄러**: 백엔드와 동일 서비스에서 별도 프로세스

### 환경 변수

필수 API 키:
- `DART_API_KEY`: [opendart.fss.or.kr](https://opendart.fss.or.kr) 발급
- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`: Naver Developers
- `YOUTUBE_API_KEY`: Google Cloud Console
- `OPENAI_API_KEY` 및/또는 `ANTHROPIC_API_KEY`

## 핵심 파일

구현 시 우선 확인할 파일:

- `backend/app/agents/graph.py` -- LangGraph 파이프라인 정의
- `backend/app/agents/state.py` -- 에이전트 간 공유 상태 스키마
- `backend/app/db/models/report.py` -- 보고서 모델 (에이전트 ↔ 프론트엔드)
- `frontend/src/app/reports/[slug]/page.tsx` -- 보고서 상세 페이지
- `knowledge/deep_value.md`, `knowledge/quality.md` -- 투자 철학

## 관련 문서

- [ROADMAP.md](../ROADMAP.md) - 구현 로드맵 (Phase 1~6)
- [README.md](../README.md) - 프로젝트 소개 및 빠른 시작

## 참고

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LiteLLM 공식 문서](https://docs.litellm.ai/)
- [DART OpenAPI 가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001)
- [pykrx 문서](https://github.com/sharebook-kr/pykrx)
