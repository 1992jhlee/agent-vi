# TODO

## 🚀 현재 작업: Phase 5 완료

> **상태 업데이트**: 2026-01-30
> - Phase 1~5 완료 (100%)
> - Phase 6 (데이터 시각화) 준비 중

---

## Phase 1: 프로젝트 기반 구축 ✅

모든 항목 완료

---

## Phase 2: 데이터 소스 & LLM ✅

모든 항목 완료

---

## Phase 3: 에이전트 파이프라인 ✅

모든 항목 완료

---

## Phase 4: API & 프론트엔드 ✅

모든 항목 완료

---

## Phase 5: 재무실적 뷰어 MVP ✅

### 백엔드
- [x] stocks.py - 종목 검색 API
- [x] financial_service.py - 증분 데이터 수집
- [x] companies.py - 종목 등록 API 수정 (BackgroundTasks)
- [x] financials.py - 재수집 API 추가
- [x] router.py - stocks 라우터 등록
- [x] **스마트 파싱**: 컨텍스트 기반 매출액 추정
- [x] **메타데이터 추적**: 추정값 여부 저장 (raw_data_json)
- [x] **데이터 수집 확장**: 6년 연간 + 8분기 데이터
- [x] **CORS 업데이트**: localhost:3001 지원

### 프론트엔드
- [x] FinancialTable.tsx - 재무표 컴포넌트
  - [x] **테이블 transpose** (행=항목, 열=연도/분기)
  - [x] **추정값 표시** (*표시 + 툴팁)
  - [x] **발표 전 표시** (미발표 데이터)
- [x] CompanyCreateModal.tsx - 자동완성 모달
- [x] companies/[stock_code]/page.tsx - 상세 페이지
  - [x] **뒤로 가기 버튼** 추가
- [x] companies/page.tsx - 목록 페이지
- [x] lib/api.ts - searchStocks 함수 추가
- [x] lib/types.ts - StockSearchResult 타입 추가

### 문서
- [x] README.md 업데이트
- [x] ROADMAP.md 업데이트
- [x] TODO.md 업데이트

---

## Phase 6: 데이터 시각화 📋

### 차트 라이브러리 설치
- [ ] Recharts 설치
  ```bash
  cd frontend
  npm install recharts
  ```

### 재무 트렌드 차트
- [ ] components/companies/FinancialChart.tsx 작성
  - [ ] 매출액 추세선
  - [ ] 영업이익 추세선
  - [ ] 순이익 추세선
  - [ ] 연간/분기 토글 버튼
- [ ] companies/[stock_code]/page.tsx에 차트 추가

### 주가 차트 (선택사항)
- [ ] StockChart.tsx 작성
  - [ ] OHLCV 캔들 차트
  - [ ] 거래량 막대 차트
  - [ ] 이동평균선 (20일, 60일, 120일)
- [ ] 주가 데이터 API 연동

### 밸류에이션 차트 (선택사항)
- [ ] ValuationChart.tsx 작성
  - [ ] PER/PBR 추세
  - [ ] 레이더 차트 (Deep Value vs Quality)

---

## Phase 7: AI 분석 재활성화 📋

### 기존 코드 재활성화
- [ ] agents/ 폴더 코드 검토
- [ ] LangGraph 파이프라인 테스트
- [ ] Knowledge Base 업데이트

### 관리자 대시보드 개선
- [ ] admin/page.tsx - 분석 실행 UI 개선
- [ ] 실시간 상태 폴링
- [ ] 에러 로그 표시

### 스케줄링
- [ ] scheduler/jobs.py - APScheduler 작업 정의
- [ ] scheduler/run.py - 스케줄러 실행
- [ ] Docker Compose profile 설정

### 투자 철학 편집 UI
- [ ] admin/knowledge/page.tsx - Markdown 에디터
- [ ] GET/PUT /api/v1/admin/knowledge/{filename} API
- [ ] 실시간 미리보기

---

## Phase 8: 배포 & 최적화 📋

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

### 완료된 주요 기능
- ✅ 종목 검색 & 자동완성
- ✅ 재무실적 표시 (연간 6년 + 분기 8분기)
- ✅ 증분 데이터 수집 (중복 방지)
- ✅ 억 원 단위 표시 & 증감률
- ✅ **스마트 파싱**: 계정과목명 차이 자동 처리
- ✅ **추정값 투명성**: * 표시 + 툴팁으로 사용자 알림
- ✅ **테이블 transpose**: 가독성 향상
- ✅ **발표 전 데이터 구분**: 미발표 실적 표시
- ✅ 기존 AI 분석 코드 유지

### 다음 세션 시작할 때
1. Phase 6 첫 항목: Recharts 설치
2. FinancialChart.tsx 작성
3. 재무 트렌드 차트 구현

---

## 참고

- [README.md](./README.md) - 프로젝트 소개
- [ROADMAP.md](./ROADMAP.md) - 전체 로드맵
- [계획서](/.claude/plans/compiled-leaping-balloon.md) - Phase 5 구현 계획
