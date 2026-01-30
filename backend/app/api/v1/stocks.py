"""
종목 검색 API

pykrx를 활용하여 전체 상장 종목 리스트를 제공하고 검색 기능을 제공합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Query
from pykrx import stock
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])


class StockInfo(BaseModel):
    """종목 정보"""
    stock_code: str
    company_name: str
    market: str


# 전체 종목 리스트 캐시
_stock_cache: List[StockInfo] = []
_cache_updated_at: datetime | None = None
_CACHE_TTL = timedelta(hours=24)  # 24시간 캐시


def _load_all_stocks() -> List[StockInfo]:
    """
    pykrx에서 전체 상장 종목 리스트를 로드합니다.
    """
    global _stock_cache, _cache_updated_at

    # 캐시가 유효하면 재사용
    if _stock_cache and _cache_updated_at:
        if datetime.now() - _cache_updated_at < _CACHE_TTL:
            logger.info(f"종목 리스트 캐시 사용 (총 {len(_stock_cache)}개)")
            return _stock_cache

    logger.info("pykrx에서 전체 종목 리스트 로드 중...")
    stocks = []

    try:
        # KOSPI 종목
        kospi_tickers = stock.get_market_ticker_list(market="KOSPI")
        for ticker in kospi_tickers:
            try:
                name = stock.get_market_ticker_name(ticker)
                stocks.append(StockInfo(
                    stock_code=ticker,
                    company_name=name,
                    market="KOSPI"
                ))
            except Exception as e:
                logger.warning(f"KOSPI 종목 {ticker} 정보 로드 실패: {e}")
                continue

        # KOSDAQ 종목
        kosdaq_tickers = stock.get_market_ticker_list(market="KOSDAQ")
        for ticker in kosdaq_tickers:
            try:
                name = stock.get_market_ticker_name(ticker)
                stocks.append(StockInfo(
                    stock_code=ticker,
                    company_name=name,
                    market="KOSDAQ"
                ))
            except Exception as e:
                logger.warning(f"KOSDAQ 종목 {ticker} 정보 로드 실패: {e}")
                continue

        _stock_cache = stocks
        _cache_updated_at = datetime.now()
        logger.info(f"종목 리스트 로드 완료: KOSPI={len(kospi_tickers)}, KOSDAQ={len(kosdaq_tickers)}, 총={len(stocks)}개")

    except Exception as e:
        logger.error(f"종목 리스트 로드 실패: {e}", exc_info=True)
        # 실패해도 기존 캐시 반환
        if _stock_cache:
            logger.info("기존 캐시 사용")
            return _stock_cache
        raise

    return stocks


@router.get("/search", response_model=List[StockInfo])
async def search_stocks(
    q: str = Query(..., min_length=1, description="검색어 (종목명 또는 종목코드)")
):
    """
    종목명 또는 종목코드로 종목을 검색합니다.

    Args:
        q: 검색어 (예: "삼성", "005930")

    Returns:
        최대 10개의 매칭되는 종목 리스트
    """
    # 전체 종목 로드
    all_stocks = _load_all_stocks()

    # 검색어 정규화 (공백 제거, 소문자화)
    query = q.strip()

    results = []

    # 1차: 완전 일치 (종목코드)
    for stock_info in all_stocks:
        if stock_info.stock_code == query:
            results.append(stock_info)

    # 2차: 종목명 시작 일치
    if len(results) < 10:
        for stock_info in all_stocks:
            if stock_info not in results:
                if stock_info.company_name.startswith(query):
                    results.append(stock_info)
                    if len(results) >= 10:
                        break

    # 3차: 종목명 부분 일치
    if len(results) < 10:
        for stock_info in all_stocks:
            if stock_info not in results:
                if query in stock_info.company_name:
                    results.append(stock_info)
                    if len(results) >= 10:
                        break

    # 4차: 종목코드 부분 일치
    if len(results) < 10:
        for stock_info in all_stocks:
            if stock_info not in results:
                if query in stock_info.stock_code:
                    results.append(stock_info)
                    if len(results) >= 10:
                        break

    logger.info(f"검색어 '{query}': {len(results)}개 결과")
    return results[:10]


@router.post("/cache/refresh")
async def refresh_cache():
    """
    종목 리스트 캐시를 강제로 새로고침합니다.
    """
    global _stock_cache, _cache_updated_at
    _stock_cache = []
    _cache_updated_at = None

    stocks = _load_all_stocks()

    return {
        "message": "캐시 갱신 완료",
        "total_stocks": len(stocks),
        "updated_at": _cache_updated_at.isoformat() if _cache_updated_at else None
    }
