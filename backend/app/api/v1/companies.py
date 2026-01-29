import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Company
from app.db.session import get_db
from app.schemas import CompanyCreate, CompanyListResponse, CompanyResponse, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    market: str | None = Query(None),
    sector: str | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None, description="Search by company name or stock code"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Company)

    if market:
        query = query.where(Company.market == market)
    if sector:
        query = query.where(Company.sector == sector)
    if is_active is not None:
        query = query.where(Company.is_active == is_active)
    if q:
        query = query.where(
            Company.company_name.ilike(f"%{q}%") | Company.stock_code.ilike(f"%{q}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
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
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate
    existing = await db.execute(
        select(Company).where(Company.stock_code == data.stock_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 등록된 종목코드입니다.")

    company = Company(**data.model_dump())
    db.add(company)
    await db.flush()
    await db.refresh(company)
    return CompanyResponse.model_validate(company)


@router.get("/{stock_code}", response_model=CompanyResponse)
async def get_company(
    stock_code: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.stock_code == stock_code))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="등록되지 않은 종목코드입니다.")
    return CompanyResponse.model_validate(company)


@router.put("/{stock_code}", response_model=CompanyResponse)
async def update_company(
    stock_code: str,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.stock_code == stock_code))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="등록되지 않은 종목코드입니다.")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)

    await db.flush()
    await db.refresh(company)
    return CompanyResponse.model_validate(company)


@router.delete("/{stock_code}")
async def delete_company(
    stock_code: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.stock_code == stock_code))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="등록되지 않은 종목코드입니다.")

    await db.delete(company)
    return {"message": f"{stock_code} 종목이 삭제되었습니다."}
