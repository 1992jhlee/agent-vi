from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisRunCreate(BaseModel):
    stock_code: str = Field(..., examples=["005930"])
    llm_model: str | None = Field(None, examples=["gpt-4o"])
    force_refresh: bool = False


class AnalysisRunResponse(BaseModel):
    id: int
    company_id: int
    status: str
    trigger_type: str
    llm_model: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalysisBatchCreate(BaseModel):
    stock_codes: list[str]
    llm_model: str | None = None
