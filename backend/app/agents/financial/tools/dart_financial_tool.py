"""DART 재무제표 조회 도구"""
from langchain_core.tools import tool

from app.data_sources.dart_client import DARTClient


@tool
def get_financial_statements(
    stock_code: str,
    year: int = 2023,
    report_type: str = "annual"
) -> str:
    """
    DART에서 재무제표를 조회합니다.

    Args:
        stock_code: 종목코드 (예: "005930")
        year: 회계연도 (기본값: 2023)
        report_type: 보고서 유형 (annual/quarter1/quarter2/quarter3)

    Returns:
        재무제표 주요 항목 요약
    """
    client = DARTClient()

    # 종목코드 → DART 기업코드
    corp_code = client.get_corp_code_by_stock_code(stock_code)
    if not corp_code:
        return f"종목코드 {stock_code}에 해당하는 기업을 찾을 수 없습니다."

    # 재무제표 조회
    df = client.get_financial_statements(
        corp_code=corp_code,
        year=year,
        report_type=report_type
    )

    if df is None or df.empty:
        return f"{year}년 {report_type} 재무제표를 찾을 수 없습니다."

    # 재무 데이터 파싱
    parsed = client.parse_financial_data(df)

    if not parsed:
        return "재무 데이터를 파싱할 수 없습니다."

    # 결과 포맷팅
    result_lines = [f"{year}년 재무제표 ({report_type}):"]

    # 주요 항목
    items = {
        "revenue": "매출액",
        "operating_income": "영업이익",
        "net_income": "당기순이익",
        "total_assets": "자산총계",
        "total_liabilities": "부채총계",
        "total_equity": "자본총계",
        "operating_cash_flow": "영업활동현금흐름",
    }

    for key, label in items.items():
        value = parsed.get(key)
        if value:
            # 조 단위로 변환
            trillion = value / 1_000_000_000_000
            result_lines.append(f"  - {label}: {trillion:.2f}조원")

    # 주요 비율 계산
    if parsed.get("total_equity") and parsed.get("net_income"):
        roe = (parsed["net_income"] / parsed["total_equity"]) * 100
        result_lines.append(f"\n주요 지표:")
        result_lines.append(f"  - ROE: {roe:.2f}%")

    if parsed.get("revenue") and parsed.get("operating_income"):
        op_margin = (parsed["operating_income"] / parsed["revenue"]) * 100
        result_lines.append(f"  - 영업이익률: {op_margin:.2f}%")

    if parsed.get("total_assets") and parsed.get("total_liabilities"):
        debt_ratio = (parsed["total_liabilities"] / parsed["total_assets"]) * 100
        result_lines.append(f"  - 부채비율: {debt_ratio:.2f}%")

    return "\n".join(result_lines)
