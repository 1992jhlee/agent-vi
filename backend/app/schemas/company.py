from datetime import datetime

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    stock_code: str = Field(..., max_length=10, examples=["005930"])
    company_name: str = Field(..., max_length=200, examples=["삼성전자"])
    company_name_en: str | None = Field(None, max_length=200, examples=["Samsung Electronics"])
    corp_code: str | None = Field(None, max_length=20)
    market: str = Field(..., max_length=10, examples=["KOSPI"])
    sector: str | None = Field(None, max_length=100, examples=["반도체"])


class CompanyUpdate(BaseModel):
    company_name: str | None = Field(None, max_length=200)
    company_name_en: str | None = Field(None, max_length=200)
    corp_code: str | None = Field(None, max_length=20)
    market: str | None = Field(None, max_length=10)
    sector: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class CompanyResponse(BaseModel):
    id: int
    stock_code: str
    company_name: str
    company_name_en: str | None
    corp_code: str | None
    market: str
    sector: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
    items: list[CompanyResponse]
