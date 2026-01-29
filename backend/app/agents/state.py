"""Shared state schema for the LangGraph analysis pipeline."""

from typing import TypedDict


class AnalysisState(TypedDict, total=False):
    # Identifiers
    company_id: int
    stock_code: str
    company_name: str
    analysis_run_id: int

    # Information Collection results
    news_articles: list[dict]
    youtube_summaries: list[dict]
    blog_analyses: list[dict]
    dart_disclosures: list[dict]
    earnings_outlook_raw: str

    # Financial Analysis results
    financial_statements: list[dict]
    stock_price_data: dict
    valuation_metrics: dict
    financial_analysis_text: str

    # Valuation results (2 categories)
    deep_value_evaluation: dict  # {score, analysis, signals}
    quality_evaluation: dict  # {score, analysis, signals}
    overall_score: float
    overall_verdict: str

    # Report output
    report_sections: dict
    report_id: int | None

    # Execution tracking
    current_stage: str
    errors: list[str]
