"""Main LangGraph graph definition for the analysis pipeline.

Pipeline flow:
    orchestrator_start
        ├── collect_information (parallel)
        └── analyze_financials  (parallel)
    orchestrator_merge
    evaluate_valuation
    generate_report
"""
import logging

from langgraph.graph import END, START, StateGraph

from app.agents.financial.agent import analyze_financials_node
from app.agents.information.agent import collect_information_node
from app.agents.report.agent import generate_report_node
from app.agents.state import AnalysisState
from app.agents.valuation.agent import evaluate_valuation_node

logger = logging.getLogger(__name__)


def orchestrator_start(state: AnalysisState) -> AnalysisState:
    """
    파이프라인 시작: 입력 검증 및 초기화

    Args:
        state: 초기 상태 (company_id, stock_code, company_name 필수)

    Returns:
        초기화된 상태
    """
    logger.info(
        f"분석 파이프라인 시작: {state.get('company_name')} ({state.get('stock_code')})"
    )

    # 필수 필드 검증
    required_fields = ["company_id", "stock_code", "company_name"]
    for field in required_fields:
        if field not in state:
            logger.error(f"필수 필드 누락: {field}")
            return {
                **state,
                "current_stage": "failed",
                "errors": [f"필수 필드 누락: {field}"],
            }

    return {
        **state,
        "current_stage": "started",
        "errors": [],
    }


def orchestrator_merge(state: AnalysisState) -> AnalysisState:
    """
    병렬 에이전트 결과 병합

    Args:
        state: 정보 수집 및 재무 분석 완료 상태

    Returns:
        병합된 상태
    """
    logger.info("병렬 에이전트 결과 병합 중...")

    # 에러 체크
    errors = state.get("errors", [])

    if errors:
        logger.warning(f"병합 단계에서 오류 발견: {errors}")
        return {
            **state,
            "current_stage": "merge_failed",
        }

    logger.info("병합 완료")

    return {
        **state,
        "current_stage": "merged",
    }


def build_graph() -> StateGraph:
    """
    분석 파이프라인 그래프 생성

    Returns:
        컴파일된 StateGraph
    """
    graph = StateGraph(AnalysisState)

    # 노드 추가
    graph.add_node("orchestrator_start", orchestrator_start)
    graph.add_node("collect_information", collect_information_node)
    graph.add_node("analyze_financials", analyze_financials_node)
    graph.add_node("orchestrator_merge", orchestrator_merge)
    graph.add_node("evaluate_valuation", evaluate_valuation_node)
    graph.add_node("generate_report", generate_report_node)

    # 엣지: START -> orchestrator
    graph.add_edge(START, "orchestrator_start")

    # Fan-out: 병렬 실행
    graph.add_edge("orchestrator_start", "collect_information")
    graph.add_edge("orchestrator_start", "analyze_financials")

    # Fan-in: 병합
    graph.add_edge("collect_information", "orchestrator_merge")
    graph.add_edge("analyze_financials", "orchestrator_merge")

    # 순차 실행: merge -> evaluate -> report -> END
    graph.add_edge("orchestrator_merge", "evaluate_valuation")
    graph.add_edge("evaluate_valuation", "generate_report")
    graph.add_edge("generate_report", END)

    logger.info("LangGraph 파이프라인 그래프 빌드 완료")

    return graph


# 컴파일된 그래프 인스턴스
analysis_graph = build_graph().compile()
