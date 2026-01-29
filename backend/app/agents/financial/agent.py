"""Financial Analysis Agent

재무제표 및 주가 데이터를 분석합니다.
"""
import logging

from app.agents.financial.prompts import ANALYSIS_PROMPT_TEMPLATE, SYSTEM_PROMPT
from app.agents.financial.tools.dart_financial_tool import get_financial_statements
from app.agents.financial.tools.stock_price_tool import get_stock_analysis
from app.agents.state import AnalysisState
from app.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)


def analyze_financials_node(state: AnalysisState) -> AnalysisState:
    """
    재무 분석 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태 (재무 분석 결과 포함)
    """
    stock_code = state["stock_code"]
    company_name = state["company_name"]

    logger.info(f"재무 분석 시작: {company_name} ({stock_code})")

    try:
        # 1. DART 재무제표 조회
        logger.info("재무제표 조회 중...")
        financial_result = get_financial_statements.invoke({
            "stock_code": stock_code,
            "year": 2023,
            "report_type": "annual"
        })

        # 2. 주가 데이터 분석
        logger.info("주가 데이터 조회 중...")
        stock_result = get_stock_analysis.invoke({
            "stock_code": stock_code,
            "days": 252
        })

        # 3. LLM을 사용하여 재무 분석
        logger.info("재무 데이터 분석 중...")

        analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            company_name=company_name,
            stock_code=stock_code,
            financial_statements=financial_result,
            stock_analysis=stock_result
        )

        llm_provider = get_llm_provider()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": analysis_prompt}
        ]

        analysis_text = llm_provider.complete(messages, temperature=0.3, max_tokens=2000)

        if not analysis_text:
            logger.error("LLM 분석 실패")
            analysis_text = "재무 분석 중 오류가 발생했습니다."

        logger.info("재무 분석 완료")

        # 상태 업데이트 (병렬 실행 시 기존 키 덮어쓰지 않기)
        return {
            "financial_statements": [{"content": financial_result}],
            "stock_price_data": {"content": stock_result},
            "financial_analysis_text": analysis_text,
        }

    except Exception as e:
        logger.error(f"재무 분석 오류: {e}", exc_info=True)

        return {
            "financial_statements": [],
            "stock_price_data": {},
            "financial_analysis_text": f"재무 분석 오류: {str(e)}",
        }
