"""Report Generation Agent

분석 결과를 종합하여 최종 보고서를 생성하고 데이터베이스에 저장합니다.
"""
import logging
from datetime import datetime

from slugify import slugify

from app.agents.report.prompts import REPORT_PROMPT_TEMPLATE, SYSTEM_PROMPT
from app.agents.state import AnalysisState
from app.db.session import get_sync_session
from app.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)


def generate_report_node(state: AnalysisState) -> AnalysisState:
    """
    보고서 생성 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태 (보고서 ID 포함)
    """
    company_name = state["company_name"]
    stock_code = state["stock_code"]
    company_id = state["company_id"]
    analysis_run_id = state.get("analysis_run_id")

    logger.info(f"보고서 생성 시작: {company_name} ({stock_code})")

    try:
        # Verdict 한글 변환
        verdict_map = {
            "strong_buy": "적극 매수",
            "buy": "매수",
            "hold": "보유",
            "sell": "매도",
            "strong_sell": "적극 매도",
        }

        overall_verdict = state.get("overall_verdict", "hold")
        overall_verdict_korean = verdict_map.get(overall_verdict, "보유")

        # LLM으로 보고서 생성
        logger.info("LLM으로 보고서 생성 중...")

        report_prompt = REPORT_PROMPT_TEMPLATE.format(
            company_name=company_name,
            stock_code=stock_code,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            information_analysis=state.get("earnings_outlook_raw", ""),
            financial_analysis=state.get("financial_analysis_text", ""),
            deep_value_score=state.get("deep_value_evaluation", {}).get("score", 50),
            deep_value_analysis=state.get("deep_value_evaluation", {}).get("analysis", ""),
            quality_score=state.get("quality_evaluation", {}).get("score", 50),
            quality_analysis=state.get("quality_evaluation", {}).get("analysis", ""),
            overall_score=state.get("overall_score", 50.0),
            overall_verdict=overall_verdict,
            overall_verdict_korean=overall_verdict_korean,
        )

        llm_provider = get_llm_provider()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": report_prompt}
        ]

        report_content = llm_provider.complete(messages, temperature=0.5, max_tokens=4000)

        if not report_content:
            logger.error("보고서 생성 실패")
            report_content = "보고서 생성 중 오류가 발생했습니다."

        # 보고서 제목 및 slug 생성
        title = f"{company_name} 투자 분석 보고서"
        slug = slugify(f"{company_name}-{stock_code}-{datetime.now().strftime('%Y%m%d')}")

        logger.info(f"보고서 데이터베이스 저장 중... slug={slug}")

        # 데이터베이스에 저장
        from app.db.models.report import AnalysisReport

        with get_sync_session() as session:
            report = AnalysisReport(
                company_id=company_id,
                analysis_run_id=analysis_run_id,
                slug=slug,
                title=title,
                report_date=datetime.now().date(),
                executive_summary=report_content[:500],  # 임시로 앞부분만
                company_overview=report_content,  # 전체 내용 (임시)
                financial_analysis="",  # TODO: 섹션별로 분리
                news_sentiment_summary="",
                earnings_outlook="",
                deep_value_evaluation=state.get("deep_value_evaluation", {}),
                quality_evaluation=state.get("quality_evaluation", {}),
                overall_score=state.get("overall_score", 50.0),
                overall_verdict=overall_verdict,
                is_published=True,
                published_at=datetime.now(),
            )

            session.add(report)
            session.commit()
            session.refresh(report)

            report_id = report.id

        logger.info(f"보고서 저장 완료: ID={report_id}, slug={slug}")

        # 상태 업데이트
        return {
            **state,
            "report_sections": {"full_report": report_content},
            "report_id": report_id,
            "current_stage": "report_generated",
        }

    except Exception as e:
        logger.error(f"보고서 생성 오류: {e}", exc_info=True)

        errors = state.get("errors", [])
        errors.append(f"보고서 생성 오류: {str(e)}")

        return {
            **state,
            "errors": errors,
            "current_stage": "report_failed",
        }
