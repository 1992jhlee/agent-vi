"""
DART (Data Analysis, Retrieval and Transfer System) API 클라이언트

OpenDartReader를 래핑하여 재무제표 및 공시 데이터를 조회합니다.
"""
import logging
from datetime import datetime
from typing import Any

import pandas as pd
import OpenDartReader

from app.config import settings

logger = logging.getLogger(__name__)


class DARTClient:
    """DART OpenAPI 클라이언트 래퍼"""

    def __init__(self, api_key: str | None = None):
        """
        Args:
            api_key: DART API 키 (기본값: settings.dart_api_key)
        """
        self.api_key = api_key or settings.dart_api_key
        if not self.api_key:
            raise ValueError("DART_API_KEY가 설정되지 않았습니다")

        self.client = OpenDartReader(self.api_key)
        logger.info("DART 클라이언트 초기화 완료")

    def get_financial_statements(
        self,
        corp_code: str,
        year: int,
        report_type: str = "annual",
        max_retries: int = 3
    ) -> pd.DataFrame | None:
        """
        재무제표 조회

        Args:
            corp_code: DART 기업코드 (예: "00126380")
            year: 회계연도 (예: 2023)
            report_type: 보고서 유형
                - "annual": 사업보고서 (연간)
                - "quarter1": 1분기보고서
                - "quarter2": 반기보고서
                - "quarter3": 3분기보고서
            max_retries: 최대 재시도 횟수

        Returns:
            재무제표 DataFrame 또는 실패 시 None
        """
        report_code_map = {
            "annual": "11011",      # 사업보고서
            "quarter1": "11013",    # 1분기보고서
            "quarter2": "11012",    # 반기보고서
            "quarter3": "11014",    # 3분기보고서
        }

        report_code = report_code_map.get(report_type)
        if not report_code:
            raise ValueError(f"지원하지 않는 보고서 유형: {report_type}")

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"재무제표 조회 시도 {attempt + 1}/{max_retries}: "
                    f"corp_code={corp_code}, year={year}, type={report_type}"
                )

                # fnlttSinglAcntAll: 재무제표 전체 (단일회사)
                df = self.client.finstate_all(
                    corp=corp_code,
                    bsns_year=year,
                    reprt_code=report_code
                )

                if df is None or df.empty:
                    logger.warning(f"재무제표 데이터가 없습니다: {corp_code} {year} {report_type}")
                    return None

                logger.info(f"재무제표 조회 성공: {len(df)} 행")
                return df

            except Exception as e:
                logger.error(
                    f"재무제표 조회 실패 (시도 {attempt + 1}/{max_retries}): {e}",
                    exc_info=True
                )
                if attempt == max_retries - 1:
                    logger.error(f"최대 재시도 횟수 초과: {corp_code}")
                    return None

        return None

    def get_company_info(self, corp_code: str) -> dict[str, Any] | None:
        """
        기업 개황 조회

        Args:
            corp_code: DART 기업코드

        Returns:
            기업 정보 딕셔너리 또는 실패 시 None
        """
        try:
            logger.info(f"기업 개황 조회: corp_code={corp_code}")
            company = self.client.company(corp_code)

            if company is None:
                logger.warning(f"기업 정보가 없습니다: {corp_code}")
                return None

            # DataFrame을 딕셔너리로 변환
            if isinstance(company, pd.DataFrame) and not company.empty:
                company_dict = company.iloc[0].to_dict()
                logger.info(f"기업 정보 조회 성공: {company_dict.get('corp_name', 'Unknown')}")
                return company_dict
            elif isinstance(company, dict):
                return company

            return None

        except Exception as e:
            logger.error(f"기업 개황 조회 실패: {e}", exc_info=True)
            return None

    def search_disclosures(
        self,
        corp_code: str,
        start_date: str,
        end_date: str,
        keyword: str | None = None,
        max_count: int = 100
    ) -> pd.DataFrame | None:
        """
        공시 검색

        Args:
            corp_code: DART 기업코드
            start_date: 시작일 (YYYYMMDD 형식)
            end_date: 종료일 (YYYYMMDD 형식)
            keyword: 검색 키워드 (선택)
            max_count: 최대 조회 건수

        Returns:
            공시 목록 DataFrame 또는 실패 시 None
        """
        try:
            logger.info(
                f"공시 검색: corp_code={corp_code}, "
                f"period={start_date}~{end_date}, keyword={keyword}"
            )

            # list 메서드: 공시 검색
            df = self.client.list(
                corp=corp_code,
                start=start_date,
                end=end_date,
                kind="",  # 전체 공시
                final=False  # 정정공시 포함
            )

            if df is None or df.empty:
                logger.warning(f"공시 데이터가 없습니다: {corp_code}")
                return None

            # 키워드 필터링
            if keyword:
                df = df[df["report_nm"].str.contains(keyword, case=False, na=False)]

            # 건수 제한
            if len(df) > max_count:
                df = df.head(max_count)

            logger.info(f"공시 검색 성공: {len(df)} 건")
            return df

        except Exception as e:
            logger.error(f"공시 검색 실패: {e}", exc_info=True)
            return None

    def get_corp_code_by_stock_code(self, stock_code: str) -> str | None:
        """
        종목코드로 DART 기업코드 조회

        Args:
            stock_code: 종목코드 (예: "005930")

        Returns:
            DART 기업코드 또는 실패 시 None
        """
        try:
            logger.info(f"기업코드 조회: stock_code={stock_code}")

            # corp_codes 속성에서 종목코드로 검색
            corp_list = self.client.corp_codes

            if corp_list is None or corp_list.empty:
                logger.error("기업코드 목록을 가져올 수 없습니다")
                return None

            # 종목코드로 필터링
            result = corp_list[corp_list["stock_code"] == stock_code]

            if result.empty:
                logger.warning(f"종목코드에 해당하는 기업을 찾을 수 없습니다: {stock_code}")
                return None

            corp_code = result.iloc[0]["corp_code"]
            corp_name = result.iloc[0]["corp_name"]
            logger.info(f"기업코드 조회 성공: {corp_name} ({corp_code})")

            return corp_code

        except Exception as e:
            logger.error(f"기업코드 조회 실패: {e}", exc_info=True)
            return None

    def parse_financial_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        재무제표 DataFrame을 구조화된 딕셔너리로 변환

        Args:
            df: get_financial_statements()에서 반환된 DataFrame

        Returns:
            파싱된 재무 데이터
        """
        if df is None or df.empty:
            return {}

        # 주요 계정과목 매핑 (계정명은 실제 DART 데이터에 맞춰 조정 필요)
        account_mapping = {
            "매출액": "revenue",
            "영업이익": "operating_income",
            "당기순이익": "net_income",
            "자산총계": "total_assets",
            "부채총계": "total_liabilities",
            "자본총계": "total_equity",
            "영업활동현금흐름": "operating_cash_flow",
            "투자활동현금흐름": "investing_cash_flow",
            "재무활동현금흐름": "financing_cash_flow",
        }

        result = {}

        try:
            for account_kr, account_en in account_mapping.items():
                # 계정과목명으로 필터링
                rows = df[df["account_nm"].str.contains(account_kr, case=False, na=False)]

                if not rows.empty:
                    # 당기 금액 추출 (thstrm_amount: 당기금액)
                    value = rows.iloc[0].get("thstrm_amount", 0)

                    # 문자열을 숫자로 변환
                    if isinstance(value, str):
                        value = value.replace(",", "")
                        value = int(float(value)) if value else 0

                    result[account_en] = value

            logger.debug(f"재무 데이터 파싱 완료: {len(result)} 항목")

        except Exception as e:
            logger.error(f"재무 데이터 파싱 오류: {e}", exc_info=True)

        return result
