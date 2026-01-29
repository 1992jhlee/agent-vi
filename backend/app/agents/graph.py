"""Main LangGraph graph definition for the analysis pipeline.

Pipeline flow:
    orchestrator_start
        ├── collect_information (parallel)
        └── analyze_financials  (parallel)
    orchestrator_merge
    evaluate_value
    generate_report
"""

from langgraph.graph import END, START, StateGraph

from app.agents.state import AnalysisState


def orchestrator_start(state: AnalysisState) -> AnalysisState:
    """Initialize the analysis run and validate inputs."""
    return {
        **state,
        "current_stage": "started",
        "errors": [],
    }


def collect_information(state: AnalysisState) -> AnalysisState:
    """Information Collection Agent: DART disclosures, news, YouTube, blogs."""
    # TODO: Implement with LLM tools
    return {
        **state,
        "current_stage": "information_collected",
        "news_articles": [],
        "youtube_summaries": [],
        "blog_analyses": [],
        "dart_disclosures": [],
        "earnings_outlook_raw": "",
    }


def analyze_financials(state: AnalysisState) -> AnalysisState:
    """Financial Analysis Agent: statements, ratios, peer comparison."""
    # TODO: Implement with LLM tools
    return {
        **state,
        "current_stage": "financials_analyzed",
        "financial_statements": [],
        "stock_price_data": {},
        "valuation_metrics": {},
        "financial_analysis_text": "",
    }


def orchestrator_merge(state: AnalysisState) -> AnalysisState:
    """Merge results from parallel agents."""
    return {
        **state,
        "current_stage": "merged",
    }


def evaluate_value(state: AnalysisState) -> AnalysisState:
    """Value Investing Evaluation Agent: Deep Value + Quality frameworks."""
    # TODO: Load knowledge/*.md files and evaluate
    return {
        **state,
        "current_stage": "evaluated",
        "deep_value_evaluation": {"score": 0, "analysis": "", "signals": []},
        "quality_evaluation": {"score": 0, "analysis": "", "signals": []},
        "overall_score": 0.0,
        "overall_verdict": "hold",
    }


def generate_report(state: AnalysisState) -> AnalysisState:
    """Report Generation Agent: synthesize and save report."""
    # TODO: Generate final report and save to DB
    return {
        **state,
        "current_stage": "report_generated",
        "report_sections": {},
        "report_id": None,
    }


def build_graph() -> StateGraph:
    """Build and return the compiled analysis pipeline graph."""
    graph = StateGraph(AnalysisState)

    # Add nodes
    graph.add_node("orchestrator_start", orchestrator_start)
    graph.add_node("collect_information", collect_information)
    graph.add_node("analyze_financials", analyze_financials)
    graph.add_node("orchestrator_merge", orchestrator_merge)
    graph.add_node("evaluate_value", evaluate_value)
    graph.add_node("generate_report", generate_report)

    # Edges: START -> orchestrator
    graph.add_edge(START, "orchestrator_start")

    # Fan-out: orchestrator -> parallel agents
    graph.add_edge("orchestrator_start", "collect_information")
    graph.add_edge("orchestrator_start", "analyze_financials")

    # Fan-in: parallel agents -> merge
    graph.add_edge("collect_information", "orchestrator_merge")
    graph.add_edge("analyze_financials", "orchestrator_merge")

    # Sequential: merge -> evaluate -> report -> END
    graph.add_edge("orchestrator_merge", "evaluate_value")
    graph.add_edge("evaluate_value", "generate_report")
    graph.add_edge("generate_report", END)

    return graph


# Compiled graph instance
analysis_graph = build_graph().compile()
