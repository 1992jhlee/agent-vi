from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    analysis_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("analysis_runs.id"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # naver_news|youtube|blog|dart_disclosure
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 to 1.0
    sentiment_label: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # positive|negative|neutral
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    company = relationship("Company", back_populates="news_articles")
    analysis_run = relationship("AnalysisRun", back_populates="news_articles")
