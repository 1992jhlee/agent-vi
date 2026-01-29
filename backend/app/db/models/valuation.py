from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ValuationMetric(Base):
    __tablename__ = "valuation_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    analysis_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_runs.id"), nullable=False
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Price Multiples
    per: Mapped[float | None] = mapped_column(Float, nullable=True)
    pbr: Mapped[float | None] = mapped_column(Float, nullable=True)
    psr: Mapped[float | None] = mapped_column(Float, nullable=True)
    pcr: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Profitability
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    roa: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_margin: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Safety
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Growth
    revenue_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    earnings_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    book_value_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Dividends
    dividend_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_payout_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Deep Value Metrics
    ncav_per_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    graham_number: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_of_safety_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Quality Metrics
    owner_earnings: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    moat_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-10

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    company = relationship("Company", back_populates="valuation_metrics")
    analysis_run = relationship("AnalysisRun", back_populates="valuation_metrics")
