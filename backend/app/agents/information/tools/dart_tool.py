"""DART 공시 검색 도구"""
from datetime import datetime, timedelta

from langchain_core.tools import tool

from app.data_sources.dart_client import DARTClient


@tool
def search_dart_disclosures(
    stock_code: str,
    days_back: int = 90
) -> str:
    """
    DART에서 최근 공시를 검색합니다.

    Args:
        stock_code: 종목코드 (예: "005930")
        days_back: 조회 기간 (일) - 기본값 90일

    Returns:
        공시 목록 (최대 10건)
    """
    client = DARTClient()

    # 종목코드 → DART 기업코드
    corp_code = client.get_corp_code_by_stock_code(stock_code)
    if not corp_code:
        return f"종목코드 {stock_code}에 해당하는 기업을 찾을 수 없습니다."

    # 검색 기간 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    # 공시 검색
    df = client.search_disclosures(
        corp_code=corp_code,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        max_count=10
    )

    if df is None or df.empty:
        return "최근 공시가 없습니다."

    # 결과 포맷팅
    result_lines = [f"최근 {days_back}일간 공시 ({len(df)}건):"]

    for _, row in df.iterrows():
        date = row.get("rcept_dt", "")
        title = row.get("report_nm", "")
        result_lines.append(f"- [{date}] {title}")

    return "\n".join(result_lines)
