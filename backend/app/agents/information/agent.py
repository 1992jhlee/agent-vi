"""Information Collection Agent

기업 관련 정보(공시, 뉴스, 블로그)를 수집하고 분석합니다.
"""
import logging

from app.agents.information.prompts import ANALYSIS_PROMPT_TEMPLATE, SYSTEM_PROMPT
from app.agents.information.tools.dart_tool import search_dart_disclosures
from app.agents.information.tools.naver_news_tool import search_naver_news
from app.agents.state import AnalysisState
from app.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)


def collect_information_node(state: AnalysisState) -> AnalysisState:
    """
    정보 수집 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태 (뉴스, 공시 정보 포함)
    """
    stock_code = state["stock_code"]
    company_name = state["company_name"]

    logger.info(f"정보 수집 시작: {company_name} ({stock_code})")

    try:
        # 1. DART 공시 검색
        logger.info("DART 공시 검색 중...")
        dart_result = search_dart_disclosures.invoke({"stock_code": stock_code, "days_back": 90})

        # 2. 네이버 뉴스 검색
        logger.info("네이버 뉴스 검색 중...")
        news_result = search_naver_news.invoke({"company_name": company_name, "max_results": 10})

        # 3. LLM을 사용하여 정보 분석
        logger.info("수집된 정보 분석 중...")

        analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            company_name=company_name,
            stock_code=stock_code,
            dart_disclosures=dart_result,
            news_articles=news_result
        )

        llm_provider = get_llm_provider()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": analysis_prompt}
        ]

        analysis_text = llm_provider.complete(messages, temperature=0.3, max_tokens=2000)

        if not analysis_text:
            logger.error("LLM 분석 실패")
            analysis_text = "정보 분석 중 오류가 발생했습니다."

        logger.info("정보 수집 완료")

        # 상태 업데이트 (병렬 실행 시 기존 키 덮어쓰지 않기)
        return {
            "dart_disclosures": [{"content": dart_result}],
            "news_articles": [{"content": news_result}],
            "earnings_outlook_raw": analysis_text,
        }

    except Exception as e:
        logger.error(f"정보 수집 오류: {e}", exc_info=True)

        return {
            "dart_disclosures": [],
            "news_articles": [],
            "earnings_outlook_raw": f"정보 수집 오류: {str(e)}",
        }
