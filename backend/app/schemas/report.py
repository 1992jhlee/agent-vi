from datetime import date, datetime

from pydantic import BaseModel


class ReportSummary(BaseModel):
    id: int
    slug: str
    title: str
    report_date: date
    company_name: str
    stock_code: str
    overall_score: float | None
    overall_verdict: str | None
    is_published: bool
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportDetail(BaseModel):
    id: int
    slug: str
    title: str
    report_date: date
    company_name: str
    stock_code: str

    # Sections
    executive_summary: str | None
    company_overview: str | None
    financial_analysis: str | None
    news_sentiment_summary: str | None
    earnings_outlook: str | None

    # Evaluations
    deep_value_evaluation: dict | None
    quality_evaluation: dict | None

    # Overall
    overall_score: float | None
    overall_verdict: str | None

    is_published: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
    items: list[ReportSummary]
