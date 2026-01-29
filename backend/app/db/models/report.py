from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    analysis_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_runs.id"), unique=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Report Sections (Markdown)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    financial_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    news_sentiment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    earnings_outlook: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Value Investing Evaluations (2 categories)
    deep_value_evaluation: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {score, analysis, signals}
    quality_evaluation: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {score, analysis, signals}

    # Overall Assessment
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    overall_verdict: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # strong_buy|buy|hold|sell|strong_sell

    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    company = relationship("Company", back_populates="reports")
    analysis_run = relationship("AnalysisRun", back_populates="report")
