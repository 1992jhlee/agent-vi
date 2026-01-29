from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Company, FinancialStatement, ValuationMetric
from app.db.session import get_db

router = APIRouter(prefix="/financials", tags=["financials"])


@router.get("/{stock_code}")
async def get_financial_statements(
    stock_code: str,
    years: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.stock_code == stock_code))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="등록되지 않은 종목코드입니다.")

    query = (
        select(FinancialStatement)
        .where(FinancialStatement.company_id == company.id)
        .order_by(FinancialStatement.fiscal_year.desc(), FinancialStatement.fiscal_quarter.desc())
        .limit(years * 4)  # Max quarterly reports
    )
    result = await db.execute(query)
    statements = result.scalars().all()

    return {
        "stock_code": stock_code,
        "company_name": company.company_name,
        "statements": [
            {
                "fiscal_year": s.fiscal_year,
                "fiscal_quarter": s.fiscal_quarter,
                "report_type": s.report_type,
                "revenue": s.revenue,
                "operating_income": s.operating_income,
                "net_income": s.net_income,
                "total_assets": s.total_assets,
                "total_liabilities": s.total_liabilities,
                "total_equity": s.total_equity,
                "operating_cash_flow": s.operating_cash_flow,
                "investing_cash_flow": s.investing_cash_flow,
                "financing_cash_flow": s.financing_cash_flow,
                "dividends_paid": s.dividends_paid,
                "shares_outstanding": s.shares_outstanding,
            }
            for s in statements
        ],
    }


@router.get("/{stock_code}/metrics")
async def get_valuation_metrics(
    stock_code: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.stock_code == stock_code))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="등록되지 않은 종목코드입니다.")

    query = (
        select(ValuationMetric)
        .where(ValuationMetric.company_id == company.id)
        .order_by(ValuationMetric.metric_date.desc())
        .limit(1)
    )
    result = await db.execute(query)
    metric = result.scalar_one_or_none()

    if not metric:
        return {"stock_code": stock_code, "metrics": None}

    return {
        "stock_code": stock_code,
        "company_name": company.company_name,
        "metric_date": metric.metric_date.isoformat(),
        "metrics": {
            "per": metric.per,
            "pbr": metric.pbr,
            "psr": metric.psr,
            "pcr": metric.pcr,
            "ev_ebitda": metric.ev_ebitda,
            "roe": metric.roe,
            "roa": metric.roa,
            "operating_margin": metric.operating_margin,
            "net_margin": metric.net_margin,
            "debt_to_equity": metric.debt_to_equity,
            "current_ratio": metric.current_ratio,
            "interest_coverage": metric.interest_coverage,
            "revenue_growth_yoy": metric.revenue_growth_yoy,
            "earnings_growth_yoy": metric.earnings_growth_yoy,
            "dividend_yield": metric.dividend_yield,
            "dividend_payout_ratio": metric.dividend_payout_ratio,
            "ncav_per_share": metric.ncav_per_share,
            "graham_number": metric.graham_number,
            "margin_of_safety_pct": metric.margin_of_safety_pct,
            "owner_earnings": metric.owner_earnings,
            "moat_score": metric.moat_score,
        },
    }
