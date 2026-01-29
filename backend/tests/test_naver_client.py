"""
네이버 검색 API 클라이언트 테스트

삼성전자 관련 뉴스 및 블로그를 검색합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import logging

from app.data_sources.naver_client import NaverClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_search_news():
    """뉴스 검색 테스트"""
    print("\n" + "=" * 80)
    print("TEST 1: 뉴스 검색")
    print("=" * 80)

    client = NaverClient()
    query = "삼성전자"

    result = await client.search_news(query=query, display=5, sort="date")

    if result and result.get("items"):
        items = result["items"]
        print(f"✓ 뉴스 검색 성공: 총 {result.get('total', 0)}건 중 {len(items)}건 조회\n")

        for idx, item in enumerate(items, 1):
            title = client.clean_html_tags(item.get("title", ""))
            pub_date = item.get("pubDate", "")
            print(f"{idx}. [{pub_date}] {title}")

        return True
    else:
        print(f"✗ 뉴스 검색 실패")
        return False


async def test_search_blog():
    """블로그 검색 테스트"""
    print("\n" + "=" * 80)
    print("TEST 2: 블로그 검색")
    print("=" * 80)

    client = NaverClient()
    query = "삼성전자 투자"

    result = await client.search_blog(query=query, display=5, sort="date")

    if result and result.get("items"):
        items = result["items"]
        print(f"✓ 블로그 검색 성공: 총 {result.get('total', 0)}건 중 {len(items)}건 조회\n")

        for idx, item in enumerate(items, 1):
            title = client.clean_html_tags(item.get("title", ""))
            description = client.clean_html_tags(item.get("description", ""))
            print(f"{idx}. {title}")
            print(f"   {description[:100]}...")

        return True
    else:
        print(f"✗ 블로그 검색 실패")
        return False


async def test_search_all():
    """뉴스 + 블로그 동시 검색 테스트"""
    print("\n" + "=" * 80)
    print("TEST 3: 뉴스 + 블로그 동시 검색")
    print("=" * 80)

    client = NaverClient()
    query = "삼성전자"

    result = await client.search_all(query=query, display_per_type=3, sort="date")

    if result:
        news_count = len(result.get("news", []))
        blog_count = len(result.get("blog", []))
        total_count = news_count + blog_count

        print(f"✓ 동시 검색 성공: 총 {total_count}건 (뉴스 {news_count}건, 블로그 {blog_count}건)\n")

        # 뉴스 샘플
        if result.get("news"):
            print("뉴스:")
            for idx, item in enumerate(result["news"][:3], 1):
                title = client.clean_html_tags(item.get("title", ""))
                print(f"  {idx}. {title}")

        # 블로그 샘플
        if result.get("blog"):
            print("\n블로그:")
            for idx, item in enumerate(result["blog"][:3], 1):
                title = client.clean_html_tags(item.get("title", ""))
                print(f"  {idx}. {title}")

        return True
    else:
        print(f"✗ 동시 검색 실패")
        return False


async def test_paginate_news():
    """뉴스 페이지네이션 테스트"""
    print("\n" + "=" * 80)
    print("TEST 4: 뉴스 페이지네이션 (30건)")
    print("=" * 80)

    client = NaverClient()
    query = "삼성전자"

    items = await client.paginate_news(
        query=query,
        total_count=30,
        display_per_page=10,
        sort="date",
        delay=0.1
    )

    if items:
        print(f"✓ 페이지네이션 성공: {len(items)}건 수집\n")

        # 처음 5개와 마지막 5개 출력
        print("처음 5개:")
        for idx, item in enumerate(items[:5], 1):
            title = client.clean_html_tags(item.get("title", ""))
            print(f"  {idx}. {title}")

        if len(items) > 10:
            print("\n...")
            print(f"\n마지막 5개:")
            for idx, item in enumerate(items[-5:], len(items) - 4):
                title = client.clean_html_tags(item.get("title", ""))
                print(f"  {idx}. {title}")

        return True
    else:
        print(f"✗ 페이지네이션 실패")
        return False


async def test_clean_html_tags():
    """HTML 태그 제거 테스트"""
    print("\n" + "=" * 80)
    print("TEST 5: HTML 태그 제거")
    print("=" * 80)

    client = NaverClient()

    test_cases = [
        "<b>삼성전자</b> 주가 상승",
        "실적 <b>호조</b>로 &quot;매수&quot; 의견",
        "<b>반도체</b> 업황 &amp; AI 수요",
    ]

    print("원본 → 정제 결과:")
    for original in test_cases:
        cleaned = client.clean_html_tags(original)
        print(f"  {original}")
        print(f"  → {cleaned}\n")

    return True


async def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 80)
    print("네이버 검색 API 클라이언트 통합 테스트")
    print("검색 키워드: 삼성전자")
    print("=" * 80)

    # TEST 1: 뉴스 검색
    await test_search_news()

    # TEST 2: 블로그 검색
    await test_search_blog()

    # TEST 3: 동시 검색
    await test_search_all()

    # TEST 4: 페이지네이션
    await test_paginate_news()

    # TEST 5: HTML 태그 제거
    await test_clean_html_tags()

    print("\n" + "=" * 80)
    print("✓ 모든 테스트 완료")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)
        print(f"\n❌ 테스트 실패: {e}")
