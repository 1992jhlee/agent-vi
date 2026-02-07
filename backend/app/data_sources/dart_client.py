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


# DART 표준 account_id (XBRL 태그) 매핑
# account_id는 회사·분기 구분 없이 동일한 항목에 동일한 코드를 사용하므로
# account_nm(회사별 자유형식 텍스트) 키워드 매칭보다 정확합니다.
# sj_div는 재무제표 종류 코드: BS(재무상태표), IS/CIS(손익계산서), CF(현금흐름표)
_ACCOUNT_MAP: dict[str, tuple[str, set[str]]] = {
    # 손익계산서 (IS: 단일, CIS: 포괄)
    "revenue":           ("ifrs-full_Revenue",          {"IS", "CIS"}),
    "operating_income":  ("dart_OperatingIncomeLoss",   {"IS", "CIS"}),
    "net_income":        ("ifrs-full_ProfitLoss",       {"IS", "CIS"}),
    # 재무상태표
    "total_assets":         ("ifrs-full_Assets",              {"BS"}),
    "total_liabilities":    ("ifrs-full_Liabilities",         {"BS"}),
    "total_equity":         ("ifrs-full_Equity",              {"BS"}),
    "current_assets":       ("ifrs-full_CurrentAssets",       {"BS"}),
    "current_liabilities":  ("ifrs-full_CurrentLiabilities",  {"BS"}),
    "inventories":          ("ifrs-full_Inventories",         {"BS"}),
    # 현금흐름표
    "operating_cash_flow":  ("ifrs-full_CashFlowsFromUsedInOperatingActivities",  {"CF"}),
    "investing_cash_flow":  ("ifrs-full_CashFlowsFromUsedInInvestingActivities",  {"CF"}),
    "financing_cash_flow":  ("ifrs-full_CashFlowsFromUsedInFinancingActivities",  {"CF"}),
    "capex":                ("ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", {"CF"}),
}

# capex를 단일 태그로 신고하지 않는 회사의 경우, 세부 유형자산 취득 태그를 합산하여 사용
_CAPEX_DETAIL_TAGS = [
    "dart_PurchaseOfLand",
    "dart_PurchaseOfMachinery",
    "dart_PurchaseOfStructure",
    "dart_PurchaseOfVehicles",
    "dart_PurchaseOfOtherPropertyPlantAndEquipment",
    "dart_PurchaseOfConstructionInProgress",
    "dart_PurchaseOfBuildings",
]


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

    def parse_financial_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        재무제표 DataFrame을 구조화된 딕셔너리로 변환

        DART의 표준 account_id (XBRL 태그)와 sj_div 코드를 사용하여
        회사·분기마다 다른 계정과목명(account_nm) 없이 정확하게 항목을 식별합니다.

        Args:
            df: get_financial_statements()에서 반환된 DataFrame

        Returns:
            파싱된 재무 데이터 딕셔너리
        """
        if df is None or df.empty:
            return {}

        result = {}

        try:
            for field, (account_id, allowed_divs) in _ACCOUNT_MAP.items():
                mask = (df["account_id"] == account_id) & (df["sj_div"].isin(allowed_divs))
                rows = df[mask]
                # OWN/CON 행이 혼재할 수 있으므로 첫 번째 유효 값을 사용
                for _, row in rows.iterrows():
                    value = self._extract_value(row.get("thstrm_amount", 0))
                    if value is not None:
                        result[field] = value
                        break

            # capex fallback: 단일 태그 미사용 시 세부 유형자산 취득 항목 합산
            if "capex" not in result:
                capex_sum = 0
                capex_found = False
                for tag in _CAPEX_DETAIL_TAGS:
                    mask = (df["account_id"] == tag) & (df["sj_div"] == "CF")
                    rows = df[mask]
                    for _, row in rows.iterrows():
                        val = self._extract_value(row.get("thstrm_amount", 0))
                        if val is not None:
                            capex_sum += val
                            capex_found = True
                            break
                if capex_found:
                    result["capex"] = capex_sum
                    logger.debug(f"capex fallback 합산: {capex_sum}")

            # capex fallback 2: 표준 계정코드 미사용 시 account_nm으로 직접 매칭
            # 일부 회사·연도에서 XBRL 태그를 사용하지 않고 자유형식 계정과목명만 신고함
            if "capex" not in result:
                _capex_nm_variants = {"유형자산 취득", "유형자산의 취득"}
                nm_mask = (
                    (df["account_id"] == "-표준계정코드 미사용-")
                    & (df["sj_div"] == "CF")
                )
                for _, row in df[nm_mask].iterrows():
                    nm = str(row.get("account_nm", "")).strip()
                    if nm in _capex_nm_variants:
                        val = self._extract_value(row.get("thstrm_amount", 0))
                        if val is not None:
                            # 회사별 부호 표현이 다를 수 있으므로 절대값으로 표준화
                            result["capex"] = abs(val)
                            logger.debug(
                                f"capex nm-fallback: nm='{nm}' "
                                f"raw={val} → {abs(val)}"
                            )
                            break

            # net_income fallback: 표준 계정코드 미사용 시 account_nm으로 직접 매칭
            if "net_income" not in result:
                # 1차: 법인세비용차감전순이익 (세전 이익, 차선책)
                mask = (df["account_id"] == "ifrs-full_ProfitLossBeforeTax") & (df["sj_div"].isin(["IS", "CIS"]))
                rows = df[mask]
                for _, row in rows.iterrows():
                    val = self._extract_value(row.get("thstrm_amount", 0))
                    if val is not None:
                        result["net_income"] = val
                        logger.debug(f"net_income fallback: ProfitLossBeforeTax = {val}")
                        break

            # net_income fallback 2: 비표준 계정과목명 매칭 (분기순이익, 당기순이익 등)
            if "net_income" not in result:
                _net_income_nm_keywords = ["분기순이익", "당기순이익", "반기순이익"]
                nm_mask = (
                    (df["account_id"] == "-표준계정코드 미사용-")
                    & (df["sj_div"].isin(["IS", "CIS"]))
                )
                # 최하위 계층의 순이익을 찾기 위해 역순으로 탐색
                candidate_rows = []
                for _, row in df[nm_mask].iterrows():
                    nm = str(row.get("account_nm", "")).strip()
                    for keyword in _net_income_nm_keywords:
                        if keyword in nm:
                            val = self._extract_value(row.get("thstrm_amount", 0))
                            if val is not None:
                                candidate_rows.append((nm, val, row.name))
                                break

                if candidate_rows:
                    # 가장 마지막 행(최하위 계층)의 순이익 사용
                    last_row = candidate_rows[-1]
                    result["net_income"] = last_row[1]
                    logger.debug(
                        f"net_income nm-fallback: nm='{last_row[0]}' value={last_row[1]} "
                        f"({len(candidate_rows)}개 후보 중 마지막 선택)"
                    )

            # 금융업 특화 파싱 (Revenue/OperatingIncomeLoss 태그 없을 때)
            if "revenue" not in result or "operating_income" not in result:
                self._parse_financial_industry(df, result)

            logger.debug(f"재무 데이터 파싱 완료: {len(result)} 항목")

        except Exception as e:
            logger.error(f"재무 데이터 파싱 오류: {e}", exc_info=True)

        return result

    def _parse_financial_industry(self, df: pd.DataFrame, result: dict):
        """
        금융업(은행, 증권, 보험 등) 재무제표 파싱

        금융업은 일반 제조업과 다른 구조를 사용:
        - Revenue 대신: 수수료수익 + 이자수익 등
        - OperatingIncomeLoss 대신: 순영업손익

        Args:
            df: 재무제표 DataFrame
            result: 파싱 결과 딕셔너리 (in-place 수정)
        """
        is_df = df[df['sj_div'].isin(['IS', 'CIS'])]

        # 1. 매출액 추정: 수수료수익 + 이자수익
        if "revenue" not in result:
            fee_income = None
            interest_income = None

            # 수수료수익
            fee_rows = is_df[is_df['account_id'] == 'ifrs-full_FeeAndCommissionIncome']
            for _, row in fee_rows.iterrows():
                val = self._extract_value(row.get('thstrm_amount', 0))
                if val is not None:
                    fee_income = val
                    break

            # 이자수익
            interest_rows = is_df[is_df['account_id'] == 'ifrs-full_RevenueFromInterest']
            for _, row in interest_rows.iterrows():
                val = self._extract_value(row.get('thstrm_amount', 0))
                if val is not None:
                    interest_income = val
                    break

            # 합산
            if fee_income is not None or interest_income is not None:
                result["revenue"] = (fee_income or 0) + (interest_income or 0)
                logger.info(
                    f"금융업 매출액 추정: 수수료수익({fee_income or 0:,}) + "
                    f"이자수익({interest_income or 0:,}) = {result['revenue']:,}"
                )

        # 2. 영업이익 추정: 순영업손익
        if "operating_income" not in result:
            # "순영업손익" account_nm으로 검색 (표준 태그 없음)
            nm_mask = is_df['account_nm'].str.contains('순영업손익', case=False, na=False)
            oi_rows = is_df[nm_mask]

            for _, row in oi_rows.iterrows():
                val = self._extract_value(row.get('thstrm_amount', 0))
                if val is not None:
                    result["operating_income"] = val
                    logger.info(f"금융업 영업이익 추정: 순영업손익 = {val:,}")
                    break

    def _extract_value(self, value: Any) -> int | None:
        """
        DART API 값을 정수로 변환
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
