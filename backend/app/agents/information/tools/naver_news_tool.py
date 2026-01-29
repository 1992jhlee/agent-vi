"""네이버 뉴스 검색 도구"""
import asyncio

from langchain_core.tools import tool

from app.data_sources.naver_client import NaverClient


@tool
def search_naver_news(
    company_name: str,
    max_results: int = 10
) -> str:
    """
    네이버에서 기업 관련 최신 뉴스를 검색합니다.

    Args:
        company_name: 기업명 (예: "삼성전자")
        max_results: 최대 결과 수 (기본값: 10)

    Returns:
        뉴스 검색 결과 요약
    """
    client = NaverClient()

    # 비동기 함수를 동기적으로 실행
    async def _search():
        return await client.search_news(
            query=company_name,
            display=max_results,
            sort="date"
        )

    try:
        result = asyncio.run(_search())
    except RuntimeError:
        # 이미 이벤트 루프가 실행 중인 경우
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_search())

    if not result or not result.get("items"):
        return f"{company_name} 관련 뉴스를 찾을 수 없습니다."

    items = result["items"]
    total = result.get("total", 0)

    # 결과 포맷팅
    result_lines = [f"{company_name} 최신 뉴스 ({total}건 중 {len(items)}건):"]

    for idx, item in enumerate(items, 1):
        title = client.clean_html_tags(item.get("title", ""))
        description = client.clean_html_tags(item.get("description", ""))
        pub_date = item.get("pubDate", "")

        result_lines.append(f"\n{idx}. {title}")
        result_lines.append(f"   날짜: {pub_date}")
        result_lines.append(f"   요약: {description[:100]}...")

    return "\n".join(result_lines)
