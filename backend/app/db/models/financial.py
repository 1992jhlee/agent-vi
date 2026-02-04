from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class FinancialStatement(Base):
    __tablename__ = "financial_statements"
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", "fiscal_quarter", name="uq_financial_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[int] = mapped_column(Integer, nullable=False)  # 1,2,3,4 (4=annual)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)  # annual|quarterly

    # Income Statement
    revenue: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    operating_income: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    net_income: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Balance Sheet
    total_assets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_liabilities: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_equity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_assets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_liabilities: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    inventories: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Cash Flow
    operating_cash_flow: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    investing_cash_flow: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    financing_cash_flow: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    capex: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Investment Metrics (from pykrx)
    per: Mapped[float | None] = mapped_column(Float, nullable=True)
    pbr: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Other
    dividends_paid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Raw data
    raw_data_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    company = relationship("Company", back_populates="financial_statements")
