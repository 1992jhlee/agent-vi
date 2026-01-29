"""
네이버 검색 API 클라이언트

네이버 개발자 센터의 검색 API를 사용하여 뉴스 및 블로그를 검색합니다.
"""
import asyncio
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class NaverClient:
    """네이버 검색 API 클라이언트"""

    BASE_URL = "https://openapi.naver.com/v1/search"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None
    ):
        """
        Args:
            client_id: 네이버 Client ID (기본값: settings.naver_client_id)
            client_secret: 네이버 Client Secret (기본값: settings.naver_client_secret)
        """
        self.client_id = client_id or settings.naver_client_id
        self.client_secret = client_secret or settings.naver_client_secret

        if not self.client_id or not self.client_secret:
            raise ValueError("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET이 설정되지 않았습니다")

        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

        logger.info("NaverClient 초기화 완료")

    async def search_news(
        self,
        query: str,
        display: int = 10,
        start: int = 1,
        sort: str = "date"
    ) -> dict[str, Any] | None:
        """
        뉴스 검색

        Args:
            query: 검색 키워드
            display: 한 번에 표시할 검색 결과 개수 (기본값: 10, 최대: 100)
            start: 검색 시작 위치 (기본값: 1, 최대: 1000)
            sort: 정렬 옵션
                - "date": 날짜순 (최신순)
                - "sim": 정확도순

        Returns:
            뉴스 검색 결과 딕셔너리 또는 실패 시 None
            {
                "total": 전체 검색 결과 개수,
                "items": [
                    {
                        "title": "제목",
                        "originallink": "원본 링크",
                        "link": "네이버 뉴스 링크",
                        "description": "요약",
                        "pubDate": "발행일"
                    },
                    ...
                ]
            }
        """
        try:
            url = f"{self.BASE_URL}/news.json"
            params = {
                "query": query,
                "display": min(display, 100),
                "start": start,
                "sort": sort
            }

            logger.info(f"뉴스 검색: query={query}, display={display}, sort={sort}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

                if response.status_code != 200:
                    logger.error(
                        f"뉴스 검색 API 오류: status={response.status_code}, "
                        f"response={response.text}"
                    )
                    return None

                data = response.json()
                logger.info(f"뉴스 검색 성공: {len(data.get('items', []))} 건")

                return data

        except Exception as e:
            logger.error(f"뉴스 검색 실패: {e}", exc_info=True)
            return None

    async def search_blog(
        self,
        query: str,
        display: int = 10,
        start: int = 1,
        sort: str = "date"
    ) -> dict[str, Any] | None:
        """
        블로그 검색

        Args:
            query: 검색 키워드
            display: 한 번에 표시할 검색 결과 개수 (기본값: 10, 최대: 100)
            start: 검색 시작 위치 (기본값: 1, 최대: 1000)
            sort: 정렬 옵션
                - "date": 날짜순 (최신순)
                - "sim": 정확도순

        Returns:
            블로그 검색 결과 딕셔너리 또는 실패 시 None
        """
        try:
            url = f"{self.BASE_URL}/blog.json"
            params = {
                "query": query,
                "display": min(display, 100),
                "start": start,
                "sort": sort
            }

            logger.info(f"블로그 검색: query={query}, display={display}, sort={sort}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

                if response.status_code != 200:
                    logger.error(
                        f"블로그 검색 API 오류: status={response.status_code}, "
                        f"response={response.text}"
                    )
                    return None

                data = response.json()
                logger.info(f"블로그 검색 성공: {len(data.get('items', []))} 건")

                return data

        except Exception as e:
            logger.error(f"블로그 검색 실패: {e}", exc_info=True)
            return None

    async def search_all(
        self,
        query: str,
        display_per_type: int = 10,
        sort: str = "date"
    ) -> dict[str, list[dict[str, Any]]]:
        """
        뉴스 + 블로그 동시 검색

        Args:
            query: 검색 키워드
            display_per_type: 각 타입별 검색 결과 개수
            sort: 정렬 옵션

        Returns:
            {
                "news": [...],
                "blog": [...]
            }
        """
        try:
            logger.info(f"뉴스+블로그 동시 검색: query={query}")

            # 병렬 실행
            news_task = self.search_news(query, display=display_per_type, sort=sort)
            blog_task = self.search_blog(query, display=display_per_type, sort=sort)

            news_result, blog_result = await asyncio.gather(news_task, blog_task)

            result = {
                "news": news_result.get("items", []) if news_result else [],
                "blog": blog_result.get("items", []) if blog_result else [],
            }

            total_count = len(result["news"]) + len(result["blog"])
            logger.info(f"동시 검색 완료: 총 {total_count} 건")

            return result

        except Exception as e:
            logger.error(f"동시 검색 실패: {e}", exc_info=True)
            return {"news": [], "blog": []}

    async def paginate_news(
        self,
        query: str,
        total_count: int = 100,
        display_per_page: int = 100,
        sort: str = "date",
        delay: float = 0.1
    ) -> list[dict[str, Any]]:
        """
        뉴스 페이지네이션 (여러 페이지 조회)

        Args:
            query: 검색 키워드
            total_count: 총 가져올 결과 개수
            display_per_page: 페이지당 결과 개수 (최대 100)
            sort: 정렬 옵션
            delay: 요청 간 대기 시간 (초) - Rate limiting 방지

        Returns:
            뉴스 아이템 리스트
        """
        try:
            all_items = []
            start = 1
            display = min(display_per_page, 100)

            logger.info(f"뉴스 페이지네이션: query={query}, total={total_count}")

            while len(all_items) < total_count and start <= 1000:
                result = await self.search_news(
                    query=query,
                    display=display,
                    start=start,
                    sort=sort
                )

                if not result or not result.get("items"):
                    break

                items = result["items"]
                all_items.extend(items)

                # 더 이상 결과가 없으면 종료
                if len(items) < display:
                    break

                start += display

                # Rate limiting 방지
                if delay > 0:
                    await asyncio.sleep(delay)

            # 요청한 개수만큼만 반환
            final_items = all_items[:total_count]

            logger.info(f"페이지네이션 완료: {len(final_items)} 건 수집")
            return final_items

        except Exception as e:
            logger.error(f"페이지네이션 실패: {e}", exc_info=True)
            return []

    def clean_html_tags(self, text: str) -> str:
        """
        HTML 태그 제거 (네이버 API 결과에 포함된 <b>, </b> 등)

        Args:
            text: 원본 텍스트

        Returns:
            HTML 태그가 제거된 텍스트
        """
        import re

        if not text:
            return ""

        # <b>, </b> 제거
        cleaned = re.sub(r"</?b>", "", text)
        # 기타 HTML 태그 제거
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        # HTML 엔티티 디코딩
        cleaned = cleaned.replace("&lt;", "<").replace("&gt;", ">")
        cleaned = cleaned.replace("&quot;", '"').replace("&apos;", "'")
        cleaned = cleaned.replace("&amp;", "&")

        return cleaned.strip()
