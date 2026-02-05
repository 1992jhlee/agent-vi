import logging
import math

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.data_sources.dart_client import DARTClient
from app.db.models import Company
from app.db.models.watchlist import Watchlist
from app.db.session import get_db
from app.schemas import CompanyCreate, CompanyListResponse, CompanyResponse
from app.services.financial_service import collect_financial_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=CompanyListResponse)
async def get_watchlist(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    market: str | None = Query(None),
    q: str | None = Query(None),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Company).join(Watchlist, Company.id == Watchlist.company_id).where(
        Watchlist.user_id == current_user
    )

    if market:
        query = query.where(Company.market == market)
    if q:
        query = query.where(
            Company.company_name.ilike(f"%{q}%") | Company.stock_code.ilike(f"%{q}%")
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Company.company_name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    companies = result.scalars().all()

    return CompanyListResponse(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
        items=[CompanyResponse.model_validate(c) for c in companies],
    )


@router.post("", response_model=CompanyResponse, status_code=201)
async def add_to_watchlist(
    data: CompanyCreate,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 종목이 DB에 없으면 생성
    result = await db.execute(select(Company).where(Company.stock_code == data.stock_code))
    company = result.scalar_one_or_none()

    if not company:
        company = Company(**data.model_dump())

        if not company.corp_code:
            try:
                dart = DARTClient()
                corp_code = dart.get_corp_code_by_stock_code(data.stock_code)
                if corp_code:
                    company.corp_code = corp_code
                    logger.info(f"DART 기업코드 조회 성공: {data.stock_code} -> {corp_code}")
            except Exception as e:
                logger.warning(f"DART 기업코드 조회 실패: {data.stock_code} - {e}")

        db.add(company)
        await db.flush()
        await db.refresh(company)

        if company.corp_code:
            background_tasks.add_task(
                collect_financial_data,
                company.id,
                company.stock_code,
                company.corp_code,
                False,
            )
            logger.info(f"재무데이터 수집 작업 예약: {company.stock_code}")
    else:
        # 기존 종목이지만 시장 정보가 빠진 경우 보완
        if not company.market and data.market:
            company.market = data.market
            logger.info(f"종목 시장 정보 보완: {data.stock_code} -> {data.market}")

    # 이미 관심종목에 있는지 확인
    existing = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user,
            Watchlist.company_id == company.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 관심종목에 추가되어 있습니다.")

    db.add(Watchlist(user_id=current_user, company_id=company.id))
    await db.commit()
    await db.refresh(company)

    return CompanyResponse.model_validate(company)


@router.delete("/{stock_code}")
async def remove_from_watchlist(
    stock_code: str,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.stock_code == stock_code))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="등록되지 않은 종목코드입니다.")

    result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user,
            Watchlist.company_id == company.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="관심종목에 추가되지 않은 종목입니다.")

    await db.delete(entry)
    await db.commit()

    return {"message": f"{stock_code} 종목이 관심종목에서 제거되었습니다."}
