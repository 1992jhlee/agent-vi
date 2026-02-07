"""
DART 웹사이트 크롤러

DART API에서 제공하지 않는 재무제표를 OpenDartReader의 list 메서드와
DART API를 조합하여 가져옵니다.
"""
import logging
from typing import Any

import OpenDartReader
from app.config import settings

logger = logging.getLogger(__name__)


class DARTWebScraper:
    """DART 웹사이트 크롤러"""

    def __init__(self):
        self.dart = OpenDartReader(settings.dart_api_key)
        logger.info("DARTWebScraper 초기화 완료")

    def get_annual_report_rcpno(self, corp_code: str, year: int) -> str | None:
        """
        사업보고서 접수번호 조회 (OpenDartReader list 메서드 사용)

        Args:
            corp_code: DART 기업코드
            year: 회계연도

        Returns:
            사업보고서 접수번호 또는 None
        """
        try:
            # 사업보고서는 다음 해 3월경 제출되므로 year+1년 초에 검색
            search_start = f"{year+1}0101"
            search_end = f"{year+1}0630"

            logger.info(f"DART 공시 검색: corp_code={corp_code}, year={year}")

            # OpenDartReader의 list 메서드로 공시 검색
            df = self.dart.list(
                corp=corp_code,
                start=search_start,
                end=search_end,
                kind="A",  # 사업보고서
                final=True  # 최종보고서만
            )

            if df is None or df.empty:
                logger.warning(f"공시 목록이 비어있음: {corp_code} {year}년")
                return None

            # 사업보고서 필터링 (제목에 "사업보고서" 포함 + 해당 연도)
            # 제목 예: "사업보고서 (2022.12)"
            for _, row in df.iterrows():
                report_nm = row.get("report_nm", "")
                if "사업보고서" in report_nm and f"({year}.12)" in report_nm:
                    rcpNo = row.get("rcept_no")
                    logger.info(f"사업보고서 발견: {year}년 (rcpNo={rcpNo})")
                    return rcpNo

            logger.warning(f"사업보고서를 찾을 수 없음: {corp_code} {year}년")
            return None

        except Exception as e:
            logger.error(f"DART 공시 검색 실패: {e}", exc_info=True)
            return None

    def get_financials_from_report(self, corp_code: str, year: int, rcpNo: str) -> dict[str, Any] | None:
        """
        사업보고서에서 재무제표 데이터 추출 (XML 파싱)

        Args:
            corp_code: DART 기업코드
            year: 회계연도
            rcpNo: 접수번호

        Returns:
            재무 데이터 딕셔너리 또는 None
        """
        try:
            from bs4 import BeautifulSoup
            import re

            logger.info(f"DART 문서 XML 파싱: rcpNo={rcpNo}")

            # OpenDartReader의 document() 메서드로 전체 XML 가져오기
            xml_content = self.dart.document(rcpNo)

            if not xml_content:
                logger.error(f"DART 문서를 가져올 수 없음: rcpNo={rcpNo}")
                return None

            # XML 파싱 (lxml 사용)
            soup = BeautifulSoup(xml_content, "xml")

            # 재무제표 파싱
            result = {}

            # 1. 손익계산서 파싱
            result.update(self._parse_income_statement_xml(soup))

            # 2. 재무상태표 파싱
            result.update(self._parse_balance_sheet_xml(soup))

            # 3. 현금흐름표 파싱
            result.update(self._parse_cash_flow_xml(soup))

            if result:
                logger.info(f"XML 파싱 성공: {len(result)}개 항목")
                return result
            else:
                logger.warning(f"XML 파싱 실패: 재무제표를 찾을 수 없음")
                return None

        except Exception as e:
            logger.error(f"XML 파싱 실패: {e}", exc_info=True)
            return None

    def _parse_income_statement_xml(self, soup) -> dict:
        """손익계산서 XML 파싱"""
        result = {}
        try:
            import re

            # DART XML에서 "포괄손익계산서" 제목을 포함하는 P 태그 찾기
            # 그 다음에 나오는 TABLE에서 데이터 추출
            title_pattern = re.compile(r"연결포괄손익계산서|포괄손익계산서|연결손익계산서", re.IGNORECASE)

            for p_tag in soup.find_all("P"):
                p_text = p_tag.get_text(strip=True)

                if not title_pattern.search(p_text):
                    continue

                # 요약/상세표는 제외
                if "요약" in p_text or "상세" in p_text or "주석" in p_text:
                    continue

                logger.debug(f"손익계산서 섹션 발견: {p_text}")

                # 이 P 태그 다음의 여러 테이블 중에서 실제 데이터 테이블 찾기 (행 수 > 10)
                table = None
                next_elem = p_tag
                for _ in range(20):  # 다음 20개 요소 확인
                    next_elem = next_elem.find_next_sibling() if next_elem else None
                    if not next_elem:
                        break
                    if next_elem.name == "TABLE":
                        rows = next_elem.find_all("TR")
                        if len(rows) > 10:  # 실제 데이터 테이블은 행이 많음
                            table = next_elem
                            logger.debug(f"  → 데이터 테이블 발견, 행 수: {len(rows)}")
                            break

                if not table:
                    logger.debug("  → 데이터 테이블을 찾을 수 없음")
                    continue

                # 테이블 내 TR(행) 순회
                for row in table.find_all("TR"):
                    cells = row.find_all(["TD", "TH", "TU", "TE"])
                    if len(cells) < 2:
                        continue

                    label = cells[0].get_text(strip=True)
                    # 당기(마지막 열) 금액 - 제41기 (당기)는 마지막에서 2번째 열, 제40기 (전기)는 마지막 열
                    # 보수적으로 마지막에서 2번째 열 사용 (당기 데이터)
                    value_text = cells[-2].get_text(strip=True) if len(cells) >= 3 else (cells[-1].get_text(strip=True) if len(cells) >= 2 else "")

                    # 매출액 또는 영업수익 (금융업) - 번호 prefix 무시
                    if re.search(r"(매출액|영업수익|수익\(수수료\)|수수료수익)", label) and "revenue" not in result:
                        value = self._parse_amount(value_text)
                        if value:
                            result["revenue"] = value
                            logger.debug(f"  매출액 발견: {label} = {value:,}")

                    # 영업이익
                    if re.search(r"(영업이익|순영업손익)", label) and "operating_income" not in result:
                        value = self._parse_amount(value_text)
                        if value:
                            result["operating_income"] = value
                            logger.debug(f"  영업이익 발견: {label} = {value:,}")

                    # 당기순이익 (지배기업 소유주)
                    if re.search(r"(지배기업|당사).*(당기순이익|분기순이익)", label) and "net_income" not in result:
                        value = self._parse_amount(value_text)
                        if value is not None:
                            result["net_income"] = value
                            logger.debug(f"  당기순이익 발견: {label} = {value:,}")

                    # 당기순이익 (일반)
                    if "net_income" not in result and re.search(r"(당기순이익|분기순이익|반기순이익)", label):
                        value = self._parse_amount(value_text)
                        if value is not None:
                            result["net_income"] = value
                            logger.debug(f"  당기순이익 발견: {label} = {value:,}")

                # 모두 찾았으면 중단
                if "revenue" in result and "operating_income" in result and "net_income" in result:
                    break

        except Exception as e:
            logger.debug(f"손익계산서 파싱 오류: {e}")

        return result

    def _parse_balance_sheet_xml(self, soup) -> dict:
        """재무상태표 XML 파싱"""
        result = {}
        try:
            import re

            # DART XML에서 "재무상태표" 제목을 포함하는 P 태그 찾기
            title_pattern = re.compile(r"연결재무상태표|재무상태표|대차대조표", re.IGNORECASE)

            for p_tag in soup.find_all("P"):
                p_text = p_tag.get_text(strip=True)

                if not title_pattern.search(p_text):
                    continue

                # 요약/상세표는 제외
                if "요약" in p_text or "상세" in p_text or "주석" in p_text:
                    continue

                logger.debug(f"재무상태표 섹션 발견: {p_text}")

                # 이 P 태그 다음의 여러 테이블 중에서 실제 데이터 테이블 찾기 (행 수 > 10)
                table = None
                next_elem = p_tag
                for _ in range(20):
                    next_elem = next_elem.find_next_sibling() if next_elem else None
                    if not next_elem:
                        break
                    if next_elem.name == "TABLE":
                        rows = next_elem.find_all("TR")
                        if len(rows) > 10:
                            table = next_elem
                            logger.debug(f"  → 데이터 테이블 발견, 행 수: {len(rows)}")
                            break

                if not table:
                    logger.debug("  → 데이터 테이블을 찾을 수 없음")
                    continue

                for row in table.find_all("TR"):
                    cells = row.find_all(["TD", "TH", "TU", "TE"])
                    if len(cells) < 2:
                        continue

                    label = cells[0].get_text(strip=True)
                    value_text = cells[-2].get_text(strip=True) if len(cells) >= 3 else (cells[-1].get_text(strip=True) if len(cells) >= 2 else "")

                    # 자산총계
                    if re.search(r"^자산총계", label) and "total_assets" not in result:
                        value = self._parse_amount(value_text)
                        if value:
                            result["total_assets"] = value
                            logger.debug(f"  자산총계 발견: {value:,}")

                    # 부채총계
                    if re.search(r"^부채총계", label) and "total_liabilities" not in result:
                        value = self._parse_amount(value_text)
                        if value:
                            result["total_liabilities"] = value
                            logger.debug(f"  부채총계 발견: {value:,}")

                    # 자본총계
                    if re.search(r"^자본총계", label) and "total_equity" not in result:
                        value = self._parse_amount(value_text)
                        if value:
                            result["total_equity"] = value
                            logger.debug(f"  자본총계 발견: {value:,}")

                # 모두 찾았으면 중단
                if all(k in result for k in ["total_assets", "total_liabilities", "total_equity"]):
                    break

        except Exception as e:
            logger.debug(f"재무상태표 파싱 오류: {e}")

        return result

    def _parse_cash_flow_xml(self, soup) -> dict:
        """현금흐름표 XML 파싱"""
        result = {}
        try:
            import re

            # DART XML에서 "현금흐름표" 제목을 포함하는 P 태그 찾기
            title_pattern = re.compile(r"연결현금흐름표|현금흐름표", re.IGNORECASE)

            for p_tag in soup.find_all("P"):
                p_text = p_tag.get_text(strip=True)

                if not title_pattern.search(p_text):
                    continue

                # 요약/상세표는 제외
                if "요약" in p_text or "상세" in p_text or "주석" in p_text:
                    continue

                logger.debug(f"현금흐름표 섹션 발견: {p_text}")

                # 이 P 태그 다음의 여러 테이블 중에서 실제 데이터 테이블 찾기 (행 수 > 10)
                table = None
                next_elem = p_tag
                for _ in range(20):
                    next_elem = next_elem.find_next_sibling() if next_elem else None
                    if not next_elem:
                        break
                    if next_elem.name == "TABLE":
                        rows = next_elem.find_all("TR")
                        if len(rows) > 10:
                            table = next_elem
                            logger.debug(f"  → 데이터 테이블 발견, 행 수: {len(rows)}")
                            break

                if not table:
                    logger.debug("  → 데이터 테이블을 찾을 수 없음")
                    continue

                for row in table.find_all("TR"):
                    cells = row.find_all(["TD", "TH", "TU", "TE"])
                    if len(cells) < 2:
                        continue

                    label = cells[0].get_text(strip=True)
                    value_text = cells[-2].get_text(strip=True) if len(cells) >= 3 else (cells[-1].get_text(strip=True) if len(cells) >= 2 else "")

                    # 영업활동현금흐름
                    if re.search(r"영업활동.*현금흐름", label) and "operating_cash_flow" not in result:
                        value = self._parse_amount(value_text)
                        if value is not None:
                            result["operating_cash_flow"] = value
                            logger.debug(f"  영업활동현금흐름 발견: {value:,}")

                    # 투자활동현금흐름
                    if re.search(r"투자활동.*현금흐름", label) and "investing_cash_flow" not in result:
                        value = self._parse_amount(value_text)
                        if value is not None:
                            result["investing_cash_flow"] = value
                            logger.debug(f"  투자활동현금흐름 발견: {value:,}")

                    # 재무활동현금흐름
                    if re.search(r"재무활동.*현금흐름", label) and "financing_cash_flow" not in result:
                        value = self._parse_amount(value_text)
                        if value is not None:
                            result["financing_cash_flow"] = value
                            logger.debug(f"  재무활동현금흐름 발견: {value:,}")

                # 모두 찾았으면 중단
                if all(k in result for k in ["operating_cash_flow", "investing_cash_flow", "financing_cash_flow"]):
                    break

        except Exception as e:
            logger.debug(f"현금흐름표 파싱 오류: {e}")

        return result

    def _parse_amount(self, text: str) -> int | None:
        """
        금액 문자열 파싱

        Args:
            text: 금액 문자열 (예: "1,234,567", "(123)", "-")

        Returns:
            파싱된 금액 (원 단위) 또는 None
        """
        try:
            import re

            # 공백, 쉼표 제거
            cleaned = text.replace(",", "").replace(" ", "").replace("\xa0", "")

            # 빈 문자열, -, N/A 처리
            if not cleaned or cleaned in ["-", "N/A", "―", "－"]:
                return None

            # 괄호는 음수 (123,456) → -123456
            if "(" in cleaned and ")" in cleaned:
                numbers = re.findall(r"\d+", cleaned)
                if numbers:
                    return -int("".join(numbers))

            # 일반 숫자 추출
            numbers = re.findall(r"-?\d+", cleaned)
            if numbers:
                return int(numbers[0])

            return None

        except (ValueError, TypeError):
            return None

# 편의 함수
def get_dart_web_financials(corp_code: str, year: int) -> dict[str, Any] | None:
    """
    DART API로 재무제표 직접 조회 (OpenDartReader fallback)

    OpenDartReader의 finstate_all이 실패하는 경우,
    list로 사업보고서를 찾아서 fnlttSinglAcnt API로 직접 조회합니다.

    Args:
        corp_code: DART 기업코드
        year: 회계연도

    Returns:
        재무 데이터 또는 None
    """
    scraper = DARTWebScraper()

    # 1. 사업보고서 찾기
    rcpNo = scraper.get_annual_report_rcpno(corp_code, year)
    if not rcpNo:
        return None

    # 2. 재무제표 추출
    return scraper.get_financials_from_report(corp_code, year, rcpNo)
