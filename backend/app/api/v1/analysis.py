from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalysisRun, Company
from app.db.session import get_db
from app.schemas import AnalysisBatchCreate, AnalysisRunCreate, AnalysisRunResponse

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/run", response_model=AnalysisRunResponse, status_code=201)
async def trigger_analysis(
    data: AnalysisRunCreate,
    db: AsyncSession = Depends(get_db),
):
    # Find company
    result = await db.execute(select(Company).where(Company.stock_code == data.stock_code))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="등록되지 않은 종목코드입니다.")

    # Create analysis run
    run = AnalysisRun(
        company_id=company.id,
        status="pending",
        trigger_type="manual",
        llm_model=data.llm_model,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    # TODO: Launch LangGraph pipeline as background task
    # await analysis_service.run_pipeline(run.id)

    return AnalysisRunResponse.model_validate(run)


@router.get("/runs", response_model=list[AnalysisRunResponse])
async def list_analysis_runs(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(limit)
    if status:
        query = query.where(AnalysisRun.status == status)

    result = await db.execute(query)
    runs = result.scalars().all()
    return [AnalysisRunResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=AnalysisRunResponse)
async def get_analysis_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="분석 실행을 찾을 수 없습니다.")
    return AnalysisRunResponse.model_validate(run)


@router.post("/batch", response_model=list[AnalysisRunResponse], status_code=201)
async def trigger_batch_analysis(
    data: AnalysisBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    runs = []
    for stock_code in data.stock_codes:
        result = await db.execute(select(Company).where(Company.stock_code == stock_code))
        company = result.scalar_one_or_none()
        if not company:
            continue

        run = AnalysisRun(
            company_id=company.id,
            status="pending",
            trigger_type="manual",
            llm_model=data.llm_model,
            started_at=datetime.utcnow(),
        )
        db.add(run)
        await db.flush()
        await db.refresh(run)
        runs.append(run)

    # TODO: Launch batch pipeline
    return [AnalysisRunResponse.model_validate(r) for r in runs]
