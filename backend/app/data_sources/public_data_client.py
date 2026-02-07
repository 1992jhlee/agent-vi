"""
금융위원회 공공데이터 API 클라이언트

주식시세정보 API를 통해 과거 시가총액 데이터를 조회합니다.
"""
import logging
from datetime import datetime, timedelta
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)


class PublicDataAPIError(Exception):
    """금융위원회 공공데이터 API 에러"""
    pass


class PublicDataClient:
    """금융위원회 공공데이터 API 클라이언트"""

    BASE_URL = "http://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService"

    def __init__(self, service_key: str):
        """
        Args:
            service_key: 공공데이터포털에서 발급받은 서비스 키
        """
        self.service_key = service_key

    def get_market_cap(self, stock_code: str, date: str) -> dict | None:
        """
        특정 일자의 시가총액 조회 (휴장일 자동 fallback)

        분기말/연말이 휴장일(토/일/공휴일)인 경우,
        가장 가까운 이전 영업일의 데이터를 자동으로 조회합니다.

        Args:
            stock_code: 종목코드 (예: "005930")
            date: YYYYMMDD 형식 (예: "20240630")

        Returns:
            {
                "date": "20240630",  # 요청한 날짜 (실제 조회 날짜와 다를 수 있음)
                "actual_date": "20240628",  # 실제 조회된 날짜 (휴장일 fallback시)
                "market_cap": 123456789000,  # 원 단위
                "close_price": 50000,
                "listed_shares": 5969783
            }
            또는 None (데이터 없음)
        """
        # 1차: 정확한 날짜로 시도
        result = self._fetch_market_data(stock_code, date)
        if result:
            result["actual_date"] = date  # 정확한 날짜로 조회 성공
            return result

        # 2차: 휴장일 → 이전 영업일 탐색 (최대 5일)
        logger.info(f"휴장일 감지: {date} → 이전 영업일 탐색")
        for days_back in range(1, 6):
            prev_date = self._subtract_days(date, days_back)
            result = self._fetch_market_data(stock_code, prev_date)
            if result:
                logger.info(f"✓ 휴장일 fallback: {date} → {prev_date} ({days_back}일 전)")
                result["actual_date"] = prev_date
                result["date"] = date  # 원래 요청한 날짜 유지
                return result

        logger.warning(f"시가총액 조회 실패: {stock_code}, {date} (5일 이내 영업일 없음)")
        return None

    def get_market_cap_batch(
        self,
        stock_code: str,
        dates: list[str]
    ) -> dict[str, dict]:
        """
        여러 일자의 시가총액 배치 조회

        Args:
            stock_code: 종목코드
            dates: ["20240331", "20240630", ...] 형식

        Returns:
            {
                "20240630": {"market_cap": 123..., "close_price": 50000},
                "20240930": {"market_cap": 456..., "close_price": 52000},
                ...
            }
        """
        results = {}
        for date in dates:
            try:
                data = self.get_market_cap(stock_code, date)
                if data:
                    results[date] = data
            except PublicDataAPIError as e:
                logger.warning(f"시가총액 조회 실패 ({stock_code}, {date}): {e}")
                continue

        return results

    @lru_cache(maxsize=5000)
    def _fetch_market_data(self, stock_code: str, date: str) -> dict | None:
        """
        내부 API 호출 (LRU 캐싱)

        과거 데이터는 불변이므로 영구 캐싱

        Args:
            stock_code: 종목코드
            date: YYYYMMDD 형식

        Returns:
            시가총액 데이터 또는 None
        """
        # 종목코드 → 종목명 변환 (API 파라미터 필요)
        stock_name = self._get_stock_name(stock_code)
        if not stock_name:
            logger.warning(f"종목명 조회 실패: {stock_code}")
            return None

        params = {
            "serviceKey": self.service_key,
            "numOfRows": 1,
            "pageNo": 1,
            "resultType": "json",
            "basDt": date,
            "itmsNm": stock_name
        }

        endpoint = f"{self.BASE_URL}/getStockPriceInfo"

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 응답 구조: response.body.items.item
            body = data.get("response", {}).get("body", {})
            items = body.get("items", {})

            # items가 빈 경우 처리
            if not items:
                return None

            item_data = items.get("item", [])

            # item이 없거나 빈 리스트인 경우
            if not item_data:
                return None

            # item이 리스트일 수도 dict일 수도 있음
            item = item_data[0] if isinstance(item_data, list) else item_data

            # 시가총액: mrktTotAmt (이미 원 단위)
            market_cap = item.get("mrktTotAmt")
            if not market_cap:
                return None

            return {
                "date": date,
                "market_cap": int(market_cap),  # 이미 원 단위
                "close_price": int(item.get("clpr", 0)),
                "listed_shares": int(item.get("lstgStCnt", 0))
            }

        except requests.RequestException as e:
            raise PublicDataAPIError(f"API 호출 실패: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise PublicDataAPIError(f"응답 파싱 실패: {e}")

    def _get_stock_name(self, stock_code: str) -> str | None:
        """
        종목코드 → 종목명 변환

        TODO: DB에서 조회하도록 개선 필요
        현재는 하드코딩된 매핑 사용

        Args:
            stock_code: 종목코드

        Returns:
            종목명 또는 None
        """
        # 주요 종목 매핑 (임시)
        stock_names = {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "051910": "LG화학",
            "006400": "삼성SDI",
            "034730": "SK",
            "005380": "현대차",
            "000270": "기아",
            "035420": "NAVER",
            "035720": "카카오",
            "068270": "셀트리온",
            "005490": "POSCO홀딩스",
            "207940": "삼성바이오로직스",
            "373220": "LG에너지솔루션",
            "003670": "포스코퓨처엠",
        }

        name = stock_names.get(stock_code)

        if not name:
            # DB에서 조회 시도
            try:
                from app.db.session import sync_session_factory
                from app.db.models import Company
                from sqlalchemy import select

                with sync_session_factory() as session:
                    result = session.execute(
                        select(Company.company_name)
                        .where(Company.stock_code == stock_code)
                    )
                    company = result.scalar_one_or_none()

                    if company:
                        # 캐싱을 위해 딕셔너리에 추가
                        stock_names[stock_code] = company
                        return company

            except Exception as e:
                logger.warning(f"DB에서 종목명 조회 실패 ({stock_code}): {e}")

        return name

    @staticmethod
    def _subtract_days(date_str: str, days: int) -> str:
        """
        날짜 문자열에서 일수를 빼기

        Args:
            date_str: YYYYMMDD 형식 (예: "20240630")
            days: 뺄 일수

        Returns:
            YYYYMMDD 형식 (예: "20240628")
        """
        date_obj = datetime.strptime(date_str, "%Y%m%d")
        new_date = date_obj - timedelta(days=days)
        return new_date.strftime("%Y%m%d")
