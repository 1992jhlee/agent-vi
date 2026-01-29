from fastapi import APIRouter

from app.api.v1 import analysis, companies, financials, health, reports

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(companies.router)
api_router.include_router(reports.router)
api_router.include_router(analysis.router)
api_router.include_router(financials.router)
