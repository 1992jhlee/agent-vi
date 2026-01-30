"""분석 파이프라인 실행 서비스"""

import logging
from datetime import datetime

from app.agents.graph import analysis_graph
from app.agents.state import AnalysisState
from app.db.models import AnalysisRun, Company
from app.db.session import get_sync_session

logger = logging.getLogger(__name__)


def run_analysis_pipeline(run_id: int, company_id: int, stock_code: str, company_name: str) -> dict:
    """
    LangGraph 분석 파이프라인을 실행합니다.

    Args:
        run_id: AnalysisRun ID
        company_id: Company ID
        stock_code: 종목코드
        company_name: 회사명

    Returns:
        최종 상태 딕셔너리
    """
    logger.info(f"분석 파이프라인 시작: {company_name}({stock_code}), run_id={run_id}")

    # 상태를 running으로 업데이트
    with get_sync_session() as session:
        run = session.get(AnalysisRun, run_id)
        if run:
            run.status = "running"
            run.started_at = datetime.utcnow()

    try:
        # 초기 상태 생성
        initial_state: AnalysisState = {
            "company_id": company_id,
            "stock_code": stock_code,
            "company_name": company_name,
            "analysis_run_id": run_id,
        }

        # LangGraph 파이프라인 실행
        final_state = analysis_graph.invoke(initial_state)

        # 성공 상태로 업데이트
        with get_sync_session() as session:
            run = session.get(AnalysisRun, run_id)
            if run:
                run.status = "completed"
                run.completed_at = datetime.utcnow()

        logger.info(f"분석 파이프라인 완료: {company_name}({stock_code})")

        return {
            "success": True,
            "run_id": run_id,
            "report_id": final_state.get("report_id"),
            "overall_score": final_state.get("overall_score"),
            "overall_verdict": final_state.get("overall_verdict"),
        }

    except Exception as e:
        logger.error(f"분석 파이프라인 실패: {company_name}({stock_code}) - {e}")

        # 실패 상태로 업데이트
        with get_sync_session() as session:
            run = session.get(AnalysisRun, run_id)
            if run:
                run.status = "failed"
                run.error_message = str(e)[:1000]
                run.completed_at = datetime.utcnow()

        return {
            "success": False,
            "run_id": run_id,
            "error": str(e),
        }


async def get_analysis_status(run_id: int) -> dict | None:
    """분석 실행 상태를 조회합니다."""
    from sqlalchemy import select
    from app.db.session import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id)
        )
        run = result.scalar_one_or_none()

        if not run:
            return None

        return {
            "id": run.id,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
        }
