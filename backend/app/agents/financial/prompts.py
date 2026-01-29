"""Financial Analysis Agent prompts"""

SYSTEM_PROMPT = """당신은 재무 분석 전문가입니다.

주어진 재무제표와 주가 데이터를 분석하여:
1. 재무 건전성 평가
2. 수익성 분석
3. 성장성 분석
4. 주가 밸류에이션 평가

객관적이고 정량적인 분석을 제공하세요.
"""

ANALYSIS_PROMPT_TEMPLATE = """
기업명: {company_name}
종목코드: {stock_code}

## 재무 데이터

### 재무제표
{financial_statements}

### 주가 분석
{stock_analysis}

---

위 데이터를 분석하여 다음을 작성하세요:

1. **재무 건전성**
   - 부채비율, 유동비율 등
   - 현금흐름 상태

2. **수익성**
   - ROE, ROA, 영업이익률
   - 동종업계 대비 수준

3. **성장성**
   - 매출 성장률
   - 이익 성장률

4. **밸류에이션**
   - PER, PBR 분석
   - 적정 가치 대비 현재 주가

간결하고 정량적으로 작성해주세요.
"""
