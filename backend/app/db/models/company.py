from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    corp_code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # KOSPI | KOSDAQ
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    analysis_runs = relationship("AnalysisRun", back_populates="company")
    financial_statements = relationship("FinancialStatement", back_populates="company")
    stock_prices = relationship("StockPrice", back_populates="company")
    news_articles = relationship("NewsArticle", back_populates="company")
    valuation_metrics = relationship("ValuationMetric", back_populates="company")
    reports = relationship("AnalysisReport", back_populates="company")
