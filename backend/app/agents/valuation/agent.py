"""Valuation Agent

투자 철학(Deep Value + Quality)을 기반으로 기업을 평가합니다.
"""
import logging
import re

from app.agents.state import AnalysisState
from app.agents.valuation.prompts import (
    DEEP_VALUE_PROMPT_TEMPLATE,
    QUALITY_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    load_knowledge_base,
)
from app.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)


def extract_score(text: str) -> int:
    """
    텍스트에서 점수를 추출합니다.

    Args:
        text: LLM 응답 텍스트

    Returns:
        추출된 점수 (0-100), 실패 시 50
    """
    # "점수: 75" 또는 "**점수**: 75" 형식 찾기
    match = re.search(r'점수[:\s*]+(\d+)', text, re.IGNORECASE)
    if match:
        score = int(match.group(1))
        return max(0, min(100, score))  # 0-100 범위로 제한

    # 숫자만 있는 경우
    match = re.search(r'\b(\d{1,3})\b', text)
    if match:
        score = int(match.group(1))
        if 0 <= score <= 100:
            return score

    logger.warning(f"점수 추출 실패, 기본값 50 사용: {text[:100]}")
    return 50


def evaluate_valuation_node(state: AnalysisState) -> AnalysisState:
    """
    가치투자 평가 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태 (Deep Value 및 Quality 평가 포함)
    """
    company_name = state["company_name"]
    stock_code = state["stock_code"]

    logger.info(f"가치투자 평가 시작: {company_name} ({stock_code})")

    try:
        # Knowledge Base 로드
        logger.info("투자 철학 로드 중...")
        knowledge = load_knowledge_base()

        financial_analysis = state.get("financial_analysis_text", "재무 분석 데이터 없음")
        stock_data = str(state.get("stock_price_data", {}))
        news_sentiment = state.get("earnings_outlook_raw", "뉴스 분석 데이터 없음")

        llm_provider = get_llm_provider()

        # 1. Deep Value 평가
        logger.info("Deep Value 평가 중...")

        deep_value_prompt = DEEP_VALUE_PROMPT_TEMPLATE.format(
            deep_value_philosophy=knowledge["deep_value"],
            company_name=company_name,
            stock_code=stock_code,
            financial_analysis=financial_analysis,
            stock_data=stock_data
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": deep_value_prompt}
        ]

        deep_value_text = llm_provider.complete(messages, temperature=0.3, max_tokens=2000)

        if not deep_value_text:
            logger.error("Deep Value 평가 실패")
            deep_value_text = "Deep Value 평가 중 오류가 발생했습니다."

        deep_value_score = extract_score(deep_value_text)

        # 2. Quality 평가
        logger.info("Quality 평가 중...")

        quality_prompt = QUALITY_PROMPT_TEMPLATE.format(
            quality_philosophy=knowledge["quality"],
            company_name=company_name,
            stock_code=stock_code,
            financial_analysis=financial_analysis,
            news_sentiment=news_sentiment
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": quality_prompt}
        ]

        quality_text = llm_provider.complete(messages, temperature=0.3, max_tokens=2000)

        if not quality_text:
            logger.error("Quality 평가 실패")
            quality_text = "Quality 평가 중 오류가 발생했습니다."

        quality_score = extract_score(quality_text)

        # 3. 종합 점수 계산 (가중 평균: Deep Value 40%, Quality 60%)
        overall_score = (deep_value_score * 0.4) + (quality_score * 0.6)

        # 4. 투자 판단
        if overall_score >= 80:
            verdict = "strong_buy"
        elif overall_score >= 65:
            verdict = "buy"
        elif overall_score >= 50:
            verdict = "hold"
        elif overall_score >= 35:
            verdict = "sell"
        else:
            verdict = "strong_sell"

        logger.info(
            f"평가 완료: Deep Value={deep_value_score}, "
            f"Quality={quality_score}, Overall={overall_score:.1f}, Verdict={verdict}"
        )

        # 상태 업데이트
        return {
            **state,
            "deep_value_evaluation": {
                "score": deep_value_score,
                "analysis": deep_value_text,
            },
            "quality_evaluation": {
                "score": quality_score,
                "analysis": quality_text,
            },
            "overall_score": overall_score,
            "overall_verdict": verdict,
            "current_stage": "valuation_completed",
        }

    except Exception as e:
        logger.error(f"가치투자 평가 오류: {e}", exc_info=True)

        errors = state.get("errors", [])
        errors.append(f"가치투자 평가 오류: {str(e)}")

        return {
            **state,
            "errors": errors,
            "current_stage": "valuation_failed",
        }
