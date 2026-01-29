"""주가 데이터 조회 도구"""
from langchain_core.tools import tool

from app.data_sources.stock_client import StockClient


@tool
def get_stock_analysis(
    stock_code: str,
    days: int = 252
) -> str:
    """
    주가 데이터 및 기술적 분석을 조회합니다.

    Args:
        stock_code: 종목코드 (예: "005930")
        days: 조회 기간 (일) - 기본값 252일 (약 1년)

    Returns:
        주가 데이터, 수익률, 52주 최고/최저가 등
    """
    client = StockClient()

    # 최근 주가 데이터
    df = client.get_recent_price(stock_code, days=days)

    if df is None or df.empty:
        return f"종목코드 {stock_code}의 주가 데이터를 찾을 수 없습니다."

    # 현재가 및 통계
    current_price = int(df["close"].iloc[-1])
    avg_price = int(df["close"].mean())
    high = int(df["high"].max())
    low = int(df["low"].min())
    market_cap = df["market_cap"].iloc[-1]

    result_lines = [f"주가 분석 ({days}일 기준):"]
    result_lines.append(f"  - 현재가: {current_price:,}원")
    result_lines.append(f"  - 평균가: {avg_price:,}원")
    result_lines.append(f"  - 최고가: {high:,}원")
    result_lines.append(f"  - 최저가: {low:,}원")
    result_lines.append(f"  - 시가총액: {market_cap / 1_000_000_000_000:.2f}조원")

    # 수익률 계산
    change_rates = client.get_price_change_rate(stock_code, days=days)

    if change_rates:
        result_lines.append(f"\n수익률:")
        if "1m" in change_rates:
            result_lines.append(f"  - 1개월: {change_rates['1m']:+.2f}%")
        if "3m" in change_rates:
            result_lines.append(f"  - 3개월: {change_rates['3m']:+.2f}%")
        if "6m" in change_rates:
            result_lines.append(f"  - 6개월: {change_rates['6m']:+.2f}%")
        if "1y" in change_rates:
            result_lines.append(f"  - 1년: {change_rates['1y']:+.2f}%")

    # 52주 최고/최저가
    week_52 = client.get_52week_high_low(stock_code)

    if week_52:
        result_lines.append(f"\n52주 기준:")
        result_lines.append(f"  - 최고가: {week_52['week_52_high']:,}원")
        result_lines.append(f"  - 최저가: {week_52['week_52_low']:,}원")
        result_lines.append(f"  - 최고가 대비: {week_52['high_ratio']:.2f}%")
        result_lines.append(f"  - 최저가 대비: {week_52['low_ratio']:.2f}%")

    # 펀더멘털 지표
    from datetime import datetime, timedelta
    date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    fundamental = client.get_fundamental_data(stock_code, date)

    if fundamental:
        result_lines.append(f"\n펀더멘털 지표:")
        if fundamental.get("per"):
            result_lines.append(f"  - PER: {fundamental['per']:.2f}")
        if fundamental.get("pbr"):
            result_lines.append(f"  - PBR: {fundamental['pbr']:.2f}")
        if fundamental.get("dividend_yield"):
            result_lines.append(f"  - 배당수익률: {fundamental['dividend_yield']:.2f}%")

    return "\n".join(result_lines)
