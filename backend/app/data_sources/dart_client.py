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


# DART 재무데이터 파싱 전략 맵 (리스트 기반 fallback)
# 각 필드는 우선순위에 따라 여러 전략을 시도합니다.
# account_id는 회사·분기 구분 없이 동일하므로 account_nm 키워드보다 정확합니다.
# sj_div는 재무제표 종류 코드: BS(재무상태표), IS/CIS(손익계산서), CF(현금흐름표)
_ACCOUNT_MAP: dict[str, list[dict[str, Any]]] = {
    # 매출액: 제조업 → 금융업
    "revenue": [
        {
            "method": "single_tag",
            "account_id": "ifrs-full_Revenue",
            "divs": {"IS", "CIS"},
            "priority": 1,
            "description": "제조업 매출액"
        },
        {
            "method": "sum",
            "account_ids": [
                "ifrs-full_FeeAndCommissionIncome",  # 수수료수익
                "ifrs-full_RevenueFromInterest"      # 이자수익
            ],
            "divs": {"IS", "CIS"},
            "priority": 2,
            "description": "금융업 매출액 (수수료+이자)"
        },
    ],

    # 영업이익: 제조업 → 금융업
    "operating_income": [
        {
            "method": "single_tag",
            "account_id": "dart_OperatingIncomeLoss",
            "divs": {"IS", "CIS"},
            "priority": 1,
            "description": "제조업 영업이익"
        },
        {
            "method": "account_nm_match",
            "keywords": ["순영업손익"],
            "divs": {"IS", "CIS"},
            "priority": 2,
            "description": "금융업 순영업손익"
        },
    ],

    # 당기순이익: 표준 → 세전이익 → 비표준
    "net_income": [
        {
            "method": "single_tag",
            "account_id": "ifrs-full_ProfitLoss",
            "divs": {"IS", "CIS"},
            "priority": 1,
            "description": "표준 당기순이익"
        },
        {
            "method": "single_tag",
            "account_id": "ifrs-full_ProfitLossBeforeTax",
            "divs": {"IS", "CIS"},
            "priority": 2,
            "description": "세전이익 (fallback)"
        },
        {
            "method": "account_nm_match",
            "keywords": ["분기순이익", "당기순이익", "반기순이익"],
            "divs": {"IS", "CIS"},
            "priority": 3,
            "description": "비표준 순이익 (최하위)"
        },
    ],

    # 재무상태표 (단일 전략)
    "total_assets": [
        {"method": "single_tag", "account_id": "ifrs-full_Assets", "divs": {"BS"}, "priority": 1}
    ],
    "total_liabilities": [
        {"method": "single_tag", "account_id": "ifrs-full_Liabilities", "divs": {"BS"}, "priority": 1}
    ],
    "total_equity": [
        {"method": "single_tag", "account_id": "ifrs-full_Equity", "divs": {"BS"}, "priority": 1}
    ],
    "current_assets": [
        {"method": "single_tag", "account_id": "ifrs-full_CurrentAssets", "divs": {"BS"}, "priority": 1}
    ],
    "current_liabilities": [
        {"method": "single_tag", "account_id": "ifrs-full_CurrentLiabilities", "divs": {"BS"}, "priority": 1}
    ],
    "inventories": [
        {"method": "single_tag", "account_id": "ifrs-full_Inventories", "divs": {"BS"}, "priority": 1}
    ],

    # 현금흐름표 (단일 전략)
    "operating_cash_flow": [
        {"method": "single_tag", "account_id": "ifrs-full_CashFlowsFromUsedInOperatingActivities", "divs": {"CF"}, "priority": 1}
    ],
    "investing_cash_flow": [
        {"method": "single_tag", "account_id": "ifrs-full_CashFlowsFromUsedInInvestingActivities", "divs": {"CF"}, "priority": 1}
    ],
    "financing_cash_flow": [
        {"method": "single_tag", "account_id": "ifrs-full_CashFlowsFromUsedInFinancingActivities", "divs": {"CF"}, "priority": 1}
    ],

    # CAPEX: 단일 태그 → 세부 합산 → account_nm 매칭
    "capex": [
        {
            "method": "single_tag",
            "account_id": "ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
            "divs": {"CF"},
            "priority": 1,
            "description": "표준 CAPEX 태그"
        },
        {
            "method": "sum",
            "account_ids": [
                "dart_PurchaseOfLand",
                "dart_PurchaseOfMachinery",
                "dart_PurchaseOfStructure",
                "dart_PurchaseOfVehicles",
                "dart_PurchaseOfOtherPropertyPlantAndEquipment",
                "dart_PurchaseOfConstructionInProgress",
                "dart_PurchaseOfBuildings",
            ],
            "divs": {"CF"},
            "priority": 2,
            "description": "세부 유형자산 취득 합산"
        },
        {
            "method": "account_nm_match",
            "keywords": ["유형자산 취득", "유형자산의 취득"],
            "divs": {"CF"},
            "priority": 3,
            "description": "비표준 CAPEX (account_nm)"
        },
    ],
}



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

                # 1차: 연결재무제표(CFS) 시도
                df = self.client.finstate_all(
                    corp=corp_code,
                    bsns_year=year,
                    reprt_code=report_code,
                    fs_div="CFS"
                )

                # 2차: 연결재무제표가 없으면 개별재무제표(OFS) 시도
                if df is None or df.empty:
                    logger.info(f"연결재무제표 없음, 개별재무제표(OFS) 시도: {corp_code} {year}")
                    df = self.client.finstate_all(
                        corp=corp_code,
                        bsns_year=year,
                        reprt_code=report_code,
                        fs_div="OFS"
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

    def _try_parse_strategy(self, df: pd.DataFrame, strategy: dict[str, Any]) -> Any | None:
        """
        단일 파싱 전략 시도

        Args:
            df: 재무제표 DataFrame
            strategy: 파싱 전략 딕셔너리

        Returns:
            파싱된 값 또는 None
        """
        method = strategy["method"]
        divs = strategy["divs"]

        if method == "single_tag":
            # 단일 account_id 조회
            account_id = strategy["account_id"]
            mask = (df["account_id"] == account_id) & (df["sj_div"].isin(divs))
            rows = df[mask]
            for _, row in rows.iterrows():
                value = self._extract_value(row.get("thstrm_amount", 0))
                if value is not None:
                    return value

        elif method == "sum":
            # 여러 account_id 합산 (금융업 매출액, CAPEX 세부 항목 등)
            account_ids = strategy["account_ids"]
            total = 0
            found_any = False
            for account_id in account_ids:
                mask = (df["account_id"] == account_id) & (df["sj_div"].isin(divs))
                rows = df[mask]
                for _, row in rows.iterrows():
                    value = self._extract_value(row.get("thstrm_amount", 0))
                    if value is not None:
                        total += value
                        found_any = True
                        break  # 첫 번째 유효 값만 사용

            if found_any:
                return total

        elif method == "account_nm_match":
            # account_nm 키워드 매칭 (비표준 계정과목)
            keywords = strategy["keywords"]
            mask = (df["account_id"] == "-표준계정코드 미사용-") & (df["sj_div"].isin(divs))

            # CAPEX는 절대값 처리
            is_capex = any("유형자산" in kw for kw in keywords)

            # net_income은 최하위 계층 사용
            is_net_income = any("순이익" in kw for kw in keywords)

            if is_net_income:
                # 최하위 계층의 순이익 (마지막 행)
                candidate_rows = []
                for _, row in df[mask].iterrows():
                    nm = str(row.get("account_nm", "")).strip()
                    for keyword in keywords:
                        if keyword in nm:
                            val = self._extract_value(row.get("thstrm_amount", 0))
                            if val is not None:
                                candidate_rows.append(val)
                                break

                if candidate_rows:
                    return candidate_rows[-1]  # 마지막 행 (최하위)

            else:
                # 일반 매칭 (첫 번째 유효 값)
                for _, row in df[mask].iterrows():
                    nm = str(row.get("account_nm", "")).strip()
                    for keyword in keywords:
                        if keyword in nm:
                            val = self._extract_value(row.get("thstrm_amount", 0))
                            if val is not None:
                                return abs(val) if is_capex else val

        return None

    def parse_financial_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        재무제표 DataFrame을 구조화된 딕셔너리로 변환 (통합 파서)

        리스트 기반 fallback 전략으로 제조업/금융업 구분 없이 통합 파싱합니다.
        각 필드는 우선순위에 따라 여러 전략을 시도하며, 첫 성공한 전략의 값을 사용합니다.

        Args:
            df: get_financial_statements()에서 반환된 DataFrame

        Returns:
            파싱된 재무 데이터 딕셔너리
        """
        if df is None or df.empty:
            return {}

        result = {}

        try:
            # 각 필드에 대해 전략 리스트 시도
            for field, strategies in _ACCOUNT_MAP.items():
                for strategy in sorted(strategies, key=lambda x: x["priority"]):
                    value = self._try_parse_strategy(df, strategy)
                    if value is not None:
                        result[field] = value
                        desc = strategy.get("description", "")
                        logger.debug(
                            f"{field} 파싱 성공: {value:,} "
                            f"(전략: {strategy['method']}, {desc})"
                        )
                        break  # 성공하면 다음 fallback 시도 안 함

            logger.debug(f"재무 데이터 파싱 완료: {len(result)} 항목")

        except Exception as e:
            logger.error(f"재무 데이터 파싱 오류: {e}", exc_info=True)

        return result

    def _extract_value(self, value: Any) -> int | None:
        """
        DART API 값을 정수로 변환 (원 단위 그대로)

        DART API는 원(KRW) 단위로 값을 반환하며,
        DB에도 원 단위 그대로 저장합니다.
        프론트엔드에서 표시 시 억원 단위로 변환합니다.
        """
        try:
            if isinstance(value, str):
                value = value.replace(",", "")
                return int(float(value)) if value else None
            elif isinstance(value, (int, float)):
                return int(value)
            return None
        except (ValueError, TypeError):
            return None
