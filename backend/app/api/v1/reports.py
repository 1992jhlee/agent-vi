import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import AnalysisReport, Company
from app.db.session import get_db
from app.schemas import ReportDetail, ReportListResponse, ReportSummary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    market: str | None = Query(None),
    verdict: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AnalysisReport)
        .join(Company)
        .where(AnalysisReport.is_published.is_(True))
    )

    if market:
        query = query.where(Company.market == market)
    if verdict:
        query = query.where(AnalysisReport.overall_verdict == verdict)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.options(joinedload(AnalysisReport.company))
        .order_by(AnalysisReport.report_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    reports = result.scalars().unique().all()

    items = []
    for report in reports:
        item = ReportSummary(
            id=report.id,
            slug=report.slug,
            title=report.title,
            report_date=report.report_date,
            company_name=report.company.company_name,
            stock_code=report.company.stock_code,
            overall_score=report.overall_score,
            overall_verdict=report.overall_verdict,
            is_published=report.is_published,
            published_at=report.published_at,
            created_at=report.created_at,
        )
        items.append(item)

    return ReportListResponse(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
        items=items,
    )


@router.get("/latest", response_model=list[ReportSummary])
async def latest_reports(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AnalysisReport)
        .join(Company)
        .where(AnalysisReport.is_published.is_(True))
        .options(joinedload(AnalysisReport.company))
        .order_by(AnalysisReport.report_date.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    reports = result.scalars().unique().all()

    return [
        ReportSummary(
            id=r.id,
            slug=r.slug,
            title=r.title,
            report_date=r.report_date,
            company_name=r.company.company_name,
            stock_code=r.company.stock_code,
            overall_score=r.overall_score,
            overall_verdict=r.overall_verdict,
            is_published=r.is_published,
            published_at=r.published_at,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get("/{slug}", response_model=ReportDetail)
async def get_report(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AnalysisReport)
        .options(joinedload(AnalysisReport.company))
        .where(AnalysisReport.slug == slug)
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    return ReportDetail(
        id=report.id,
        slug=report.slug,
        title=report.title,
        report_date=report.report_date,
        company_name=report.company.company_name,
        stock_code=report.company.stock_code,
        executive_summary=report.executive_summary,
        company_overview=report.company_overview,
        financial_analysis=report.financial_analysis,
        news_sentiment_summary=report.news_sentiment_summary,
        earnings_outlook=report.earnings_outlook,
        deep_value_evaluation=report.deep_value_evaluation,
        quality_evaluation=report.quality_evaluation,
        overall_score=report.overall_score,
        overall_verdict=report.overall_verdict,
        is_published=report.is_published,
        published_at=report.published_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get("/company/{stock_code}", response_model=list[ReportSummary])
async def get_company_reports(
    stock_code: str,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AnalysisReport)
        .join(Company)
        .where(Company.stock_code == stock_code)
        .where(AnalysisReport.is_published.is_(True))
        .options(joinedload(AnalysisReport.company))
        .order_by(AnalysisReport.report_date.desc())
    )
    result = await db.execute(query)
    reports = result.scalars().unique().all()

    return [
        ReportSummary(
            id=r.id,
            slug=r.slug,
            title=r.title,
            report_date=r.report_date,
            company_name=r.company.company_name,
            stock_code=r.company.stock_code,
            overall_score=r.overall_score,
            overall_verdict=r.overall_verdict,
            is_published=r.is_published,
            published_at=r.published_at,
            created_at=r.created_at,
        )
        for r in reports
    ]
