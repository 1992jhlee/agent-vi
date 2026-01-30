import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalysisRun, Company
from app.db.session import get_db
from app.schemas import AnalysisBatchCreate, AnalysisRunCreate, AnalysisRunResponse
from app.services.analysis_service import run_analysis_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])

# 스레드풀 (LangGraph는 동기 실행이므로)
executor = ThreadPoolExecutor(max_workers=2)


def _run_pipeline_in_thread(run_id: int, company_id: int, stock_code: str, company_name: str):
    """스레드에서 파이프라인을 실행합니다."""
    try:
        result = run_analysis_pipeline(run_id, company_id, stock_code, company_name)
        logger.info(f"파이프라인 완료: {result}")
    except Exception as e:
        logger.error(f"파이프라인 실행 오류: {e}")


@router.post("/run", response_model=AnalysisRunResponse, status_code=201)
async def trigger_analysis(
    data: AnalysisRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """단일 종목 분석을 시작합니다."""
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
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    # 백그라운드에서 파이프라인 실행 (스레드풀 사용)
    executor.submit(
        _run_pipeline_in_thread,
        run.id,
        company.id,
        company.stock_code,
        company.company_name,
    )

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
    """여러 종목을 동시에 분석합니다."""
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
        )
        db.add(run)
        await db.flush()
        await db.refresh(run)
        runs.append((run, company))

    # 각 분석을 백그라운드에서 실행
    for run, company in runs:
        executor.submit(
            _run_pipeline_in_thread,
            run.id,
            company.id,
            company.stock_code,
            company.company_name,
        )

    return [AnalysisRunResponse.model_validate(r) for r, _ in runs]


@router.get("/status/{run_id}")
async def get_analysis_status(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """분석 실행의 현재 상태를 조회합니다."""
    from sqlalchemy.orm import joinedload

    result = await db.execute(
        select(AnalysisRun)
        .options(joinedload(AnalysisRun.company))
        .where(AnalysisRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="분석 실행을 찾을 수 없습니다.")

    # 완료된 경우 보고서 정보도 함께 반환
    from app.db.models import AnalysisReport

    report_info = None
    if run.status == "completed":
        report_result = await db.execute(
            select(AnalysisReport)
            .where(AnalysisReport.analysis_run_id == run_id)
            .order_by(AnalysisReport.created_at.desc())
            .limit(1)
        )
        report = report_result.scalar_one_or_none()
        if report:
            report_info = {
                "id": report.id,
                "slug": report.slug,
                "overall_score": report.overall_score,
                "overall_verdict": report.overall_verdict,
            }

    return {
        "id": run.id,
        "company_name": run.company.company_name if run.company else None,
        "stock_code": run.company.stock_code if run.company else None,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
        "report": report_info,
    }
