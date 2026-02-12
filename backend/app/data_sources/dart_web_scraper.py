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


class XMLTableFinder:
    """
    XML에서 재무제표 테이블을 찾는 다중 전략 클래스

    다양한 연도의 DART XML 구조를 지원하기 위해 여러 전략을 시도합니다.
    """

    @staticmethod
    def find_table(soup, section_type: str, p_tag=None):
        """
        재무제표 테이블 찾기 (다중 전략)

        Args:
            soup: BeautifulSoup 객체
            section_type: "income", "balance", "cash_flow"
            p_tag: 섹션 제목 P 태그 (선택, via_p_tag 전략용)

        Returns:
            (table, p_tag) 튜플 또는 (None, None)
        """
        strategies = [
            XMLTableFinder._find_via_p_tag,         # 2022년 스타일
            XMLTableFinder._find_via_keyword,       # 콘텐츠 기반 탐색
        ]

        for strategy in strategies:
            try:
                if p_tag and strategy == XMLTableFinder._find_via_p_tag:
                    # via_p_tag는 이미 p_tag가 주어진 경우
                    table = strategy(soup, section_type, p_tag)
                else:
                    table, found_p_tag = strategy(soup, section_type)
                    if table and XMLTableFinder._validate_table(table, section_type):
                        logger.info(f"테이블 발견: {strategy.__name__} ({section_type})")
                        return table, found_p_tag

            except Exception as e:
                logger.debug(f"{strategy.__name__} 실패: {e}")

        return None, None

    @staticmethod
    def _find_via_p_tag(soup, section_type: str, p_tag=None):
        """
        P 태그 기반 테이블 찾기 (2022년 스타일)

        Returns:
            (table, p_tag) 튜플
        """
        import re

        # 섹션 타입에 따른 제목 패턴
        title_patterns = {
            "income": re.compile(r"연결포괄손익계산서|포괄손익계산서|연결손익계산서", re.IGNORECASE),
            "balance": re.compile(r"연결재무상태표|재무상태표|대차대조표", re.IGNORECASE),
            "cash_flow": re.compile(r"연결현금흐름표|현금흐름표", re.IGNORECASE),
        }

        title_pattern = title_patterns.get(section_type)
        if not title_pattern:
            return None, None

        # P 태그가 주어지지 않으면 찾기
        if not p_tag:
            for p in soup.find_all("P"):
                p_text = p.get_text(strip=True)
                if title_pattern.search(p_text):
                    # 요약/상세표/주석/영향 제외
                    if any(kw in p_text for kw in ["요약", "상세", "주석", "영향", "변경"]):
                        continue
                    p_tag = p
                    break

        if not p_tag:
            return None, None

        # P 태그 다음의 TABLE 찾기
        table = None
        is_primary = bool(re.match(r'^[①②③④⑤가나다라①-⑨]\.?\s', p_tag.get_text(strip=True)))

        # 1차: siblings
        next_elem = p_tag
        for _ in range(15):
            next_elem = next_elem.find_next_sibling() if next_elem else None
            if not next_elem:
                break
            if next_elem.name == "TABLE":
                rows = next_elem.find_all("TR")
                min_rows = 5 if is_primary else 10
                if len(rows) > min_rows:
                    table = next_elem
                    break

        # 2차: find_next
        if not table:
            current = p_tag
            for _ in range(30):
                current = current.find_next("TABLE")
                if not current:
                    break
                rows = current.find_all("TR")
                min_rows = 5 if is_primary else 10
                if len(rows) > min_rows:
                    table = current
                    break

        return table, p_tag

    @staticmethod
    def _find_via_keyword(soup, section_type: str):
        """
        키워드 기반 테이블 찾기 (fallback)

        TABLE 내 콘텐츠를 검색하여 재무제표 테이블 식별

        Returns:
            (table, None) 튜플 (p_tag 없음)
        """
        import re

        # 섹션별 필수 키워드
        required_keywords = {
            "income": ["매출액", "영업이익", "순이익"],
            "balance": ["자산총계", "부채총계", "자본총계"],
            "cash_flow": ["영업활동", "투자활동", "재무활동"],
        }

        keywords = required_keywords.get(section_type, [])
        if not keywords:
            return None, None

        for table in soup.find_all("TABLE"):
            text = table.get_text()
            # 모든 필수 키워드가 포함되어 있는지 확인
            if all(kw in text for kw in keywords):
                if XMLTableFinder._validate_table(table, section_type):
                    return table, None

        return None, None

    @staticmethod
    def _validate_table(table, section_type: str) -> bool:
        """
        테이블 검증 (다중 신호)

        Args:
            table: BeautifulSoup 테이블 객체
            section_type: "income", "balance", "cash_flow"

        Returns:
            검증 통과 여부
        """
        import re

        rows = table.find_all("TR")

        # 1. 최소 행 수
        if len(rows) < 5:
            logger.debug(f"검증 실패: 행 수 부족 ({len(rows)} < 5)")
            return False

        # 2. 열 개수 (재무제표는 보통 2-5열)
        sample_row = rows[1] if len(rows) > 1 else rows[0]
        cols = sample_row.find_all(["TD", "TH"])
        if not (2 <= len(cols) <= 10):  # 10으로 완화 (더 많은 연도 포함 가능)
            logger.debug(f"검증 실패: 열 수 이상 ({len(cols)})")
            return False

        # 3. 숫자 포함 여부 (최소 3개 행에 숫자가 있어야 함)
        numeric_rows = 0
        for row in rows[:15]:  # 상위 15개 행 검사
            text = row.get_text()
            if re.search(r'\d{1,3}(,\d{3})*', text):  # 쉼표로 구분된 숫자
                numeric_rows += 1

        if numeric_rows < 3:
            logger.debug(f"검증 실패: 숫자 행 부족 ({numeric_rows} < 3)")
            return False

        # 4. 섹션별 필수 키워드 확인
        required_keywords = {
            "income": ["매출", "이익"],
            "balance": ["자산", "부채"],
            "cash_flow": ["현금", "흐름"],
        }

        keywords = required_keywords.get(section_type, [])
        table_text = table.get_text()
        if not any(kw in table_text for kw in keywords):
            logger.debug(f"검증 실패: 필수 키워드 없음 ({section_type})")
            return False

        return True


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

    def get_financials_from_report(self, corp_code: str, year: int, rcpNo: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """
        사업보고서에서 재무제표 데이터 추출 (XML 파싱)

        Args:
            corp_code: DART 기업코드
            year: 회계연도
            rcpNo: 접수번호

        Returns:
            (재무 데이터 딕셔너리, 메타데이터 딕셔너리) 튜플
            실패 시 (None, {})
        """
        try:
            from bs4 import BeautifulSoup
            import re

            logger.info(f"DART 문서 XML 파싱: rcpNo={rcpNo}")

            # OpenDartReader의 document() 메서드로 전체 XML 가져오기
            xml_content = self.dart.document(rcpNo)

            if not xml_content:
                logger.error(f"DART 문서를 가져올 수 없음: rcpNo={rcpNo}")
                return None, {}

            # XML 파싱 (lxml 사용)
            soup = BeautifulSoup(xml_content, "xml")

            # 재무제표 파싱 (메타데이터 포함)
            result = {}
            metadata = {
                "parsing_details": {},
                "unit_conversion": {}
            }

            # 1. 손익계산서 파싱
            is_data, is_meta = self._parse_income_statement_xml(soup)
            result.update(is_data)
            metadata["parsing_details"].update(is_meta.get("parsing_details", {}))
            if "unit_conversion" in is_meta:
                metadata["unit_conversion"]["income_statement"] = is_meta["unit_conversion"]

            # 2. 재무상태표 파싱
            bs_data, bs_meta = self._parse_balance_sheet_xml(soup)
            result.update(bs_data)
            metadata["parsing_details"].update(bs_meta.get("parsing_details", {}))
            if "unit_conversion" in bs_meta:
                metadata["unit_conversion"]["balance_sheet"] = bs_meta["unit_conversion"]

            # 3. 현금흐름표 파싱
            cf_data, cf_meta = self._parse_cash_flow_xml(soup)
            result.update(cf_data)
            metadata["parsing_details"].update(cf_meta.get("parsing_details", {}))
            if "unit_conversion" in cf_meta:
                metadata["unit_conversion"]["cash_flow"] = cf_meta["unit_conversion"]

            if result:
                logger.info(f"XML 파싱 성공: {len(result)}개 항목")
                return result, metadata
            else:
                logger.warning(f"XML 파싱 실패: 재무제표를 찾을 수 없음")
                return None, {}

        except Exception as e:
            logger.error(f"XML 파싱 실패: {e}", exc_info=True)
            return None, {}

    def _parse_income_statement_xml(self, soup) -> tuple[dict, dict]:
        """
        손익계산서 XML 파싱

        Returns:
            (data, metadata) 튜플
        """
        result = {}
        metadata = {"parsing_details": {}, "unit_conversion": {}}

        try:
            import re

            # DART XML에서 "포괄손익계산서" 제목을 포함하는 P 태그 찾기
            # 그 다음에 나오는 TABLE에서 데이터 추출
            title_pattern = re.compile(r"연결포괄손익계산서|포괄손익계산서|연결손익계산서", re.IGNORECASE)

            table_unit = None  # 테이블 단위

            for p_tag in soup.find_all("P"):
                p_text = p_tag.get_text(strip=True)

                if not title_pattern.search(p_text):
                    continue

                # 요약/상세표/주석/영향 제외
                if any(kw in p_text for kw in ["요약", "상세", "주석", "영향", "변경"]):
                    continue

                logger.debug(f"손익계산서 섹션 발견: {p_text}")

                # 제목이 번호로 시작하면 (예: "②", "나.") 우선순위 높음
                is_primary_section = bool(re.match(r'^[①②③④⑤가나다라①-⑨]\.?\s', p_text))

                # 이 P 태그 다음의 TABLE 찾기 (sibling뿐만 아니라 모든 다음 요소)
                table = None

                # 1차 시도: siblings 중에서 찾기 (빠름)
                next_elem = p_tag
                for _ in range(15):
                    next_elem = next_elem.find_next_sibling() if next_elem else None
                    if not next_elem:
                        break
                    if next_elem.name == "TABLE":
                        rows = next_elem.find_all("TR")
                        min_rows = 5 if is_primary_section else 10
                        if len(rows) > min_rows:
                            table = next_elem
                            logger.debug(f"  → 데이터 테이블 발견 (sibling), 행 수: {len(rows)}")
                            break

                # 2차 시도: 모든 다음 요소에서 찾기 (느리지만 확실)
                if not table:
                    current = p_tag
                    for _ in range(30):  # 더 멀리 탐색
                        current = current.find_next("TABLE")
                        if not current:
                            break
                        rows = current.find_all("TR")
                        min_rows = 5 if is_primary_section else 10
                        if len(rows) > min_rows:
                            table = current
                            logger.debug(f"  → 데이터 테이블 발견 (find_next), 행 수: {len(rows)}")
                            break

                if not table:
                    logger.debug("  → 데이터 테이블을 찾을 수 없음")
                    continue

                # 테이블에서 단위 추출 (다중 전략)
                table_unit, detected_method = self._get_unit_for_table(p_tag, table)
                if table_unit:
                    logger.info(f"손익계산서 단위 감지: {table_unit} (방법: {detected_method})")
                    metadata["unit_conversion"]["table_unit"] = table_unit
                    metadata["unit_conversion"]["detected_method"] = detected_method
                else:
                    logger.warning("손익계산서 단위 미감지 → 휴리스틱 사용")
                    metadata["unit_conversion"]["detected_method"] = detected_method

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
                        value = self._parse_amount(value_text, table_unit)
                        if value:
                            result["revenue"] = value
                            metadata["parsing_details"]["revenue"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  매출액 발견: {label} = {value:,}")

                    # 영업이익
                    if re.search(r"(영업이익|순영업손익)", label) and "operating_income" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value:
                            result["operating_income"] = value
                            metadata["parsing_details"]["operating_income"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  영업이익 발견: {label} = {value:,}")

                    # 당기순이익 (지배기업 소유주)
                    if re.search(r"(지배기업|당사).*(당기순이익|분기순이익)", label) and "net_income" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value is not None:
                            result["net_income"] = value
                            metadata["parsing_details"]["net_income"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  당기순이익 발견: {label} = {value:,}")

                    # 당기순이익 (일반)
                    if "net_income" not in result and re.search(r"(당기순이익|분기순이익|반기순이익)", label):
                        value = self._parse_amount(value_text, table_unit)
                        if value is not None:
                            result["net_income"] = value
                            metadata["parsing_details"]["net_income"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "medium"
                            }
                            logger.debug(f"  당기순이익 발견: {label} = {value:,}")

                # 모두 찾았으면 중단
                if "revenue" in result and "operating_income" in result and "net_income" in result:
                    break

        except Exception as e:
            logger.debug(f"손익계산서 파싱 오류: {e}")

        return result, metadata

    def _parse_balance_sheet_xml(self, soup) -> tuple[dict, dict]:
        """
        재무상태표 XML 파싱

        Returns:
            (data, metadata) 튜플
        """
        result = {}
        metadata = {"parsing_details": {}, "unit_conversion": {}}
        try:
            import re

            # DART XML에서 "재무상태표" 제목을 포함하는 P 태그 찾기
            title_pattern = re.compile(r"연결재무상태표|재무상태표|대차대조표", re.IGNORECASE)

            table_unit = None

            for p_tag in soup.find_all("P"):
                p_text = p_tag.get_text(strip=True)

                if not title_pattern.search(p_text):
                    continue

                # 요약/상세표/주석/영향 제외
                if any(kw in p_text for kw in ["요약", "상세", "주석", "영향", "변경"]):
                    continue

                logger.debug(f"재무상태표 섹션 발견: {p_text}")

                # 제목이 번호로 시작하면 우선순위 높음
                is_primary_section = bool(re.match(r'^[①②③④⑤가나다라①-⑨]\.?\s', p_text))

                # 이 P 태그 다음의 TABLE 찾기
                table = None

                # 1차: siblings, 2차: 모든 다음 요소
                next_elem = p_tag
                for _ in range(15):
                    next_elem = next_elem.find_next_sibling() if next_elem else None
                    if not next_elem:
                        break
                    if next_elem.name == "TABLE":
                        rows = next_elem.find_all("TR")
                        min_rows = 5 if is_primary_section else 10
                        if len(rows) > min_rows:
                            table = next_elem
                            logger.debug(f"  → 데이터 테이블 발견 (sibling), 행 수: {len(rows)}")
                            break

                if not table:
                    current = p_tag
                    for _ in range(30):
                        current = current.find_next("TABLE")
                        if not current:
                            break
                        rows = current.find_all("TR")
                        min_rows = 5 if is_primary_section else 10
                        if len(rows) > min_rows:
                            table = current
                            logger.debug(f"  → 데이터 테이블 발견 (find_next), 행 수: {len(rows)}")
                            break

                if not table:
                    logger.debug("  → 데이터 테이블을 찾을 수 없음")
                    continue

                # 다중 전략으로 단위 추출
                table_unit, detected_method = self._get_unit_for_table(p_tag, table)
                if table_unit:
                    logger.info(f"재무상태표 단위 감지: {table_unit} (방법: {detected_method})")
                    metadata["unit_conversion"]["table_unit"] = table_unit
                    metadata["unit_conversion"]["detected_method"] = detected_method
                else:
                    logger.warning("재무상태표 단위 미감지 → 휴리스틱 사용")
                    metadata["unit_conversion"]["detected_method"] = detected_method

                for row in table.find_all("TR"):
                    cells = row.find_all(["TD", "TH", "TU", "TE"])
                    if len(cells) < 2:
                        continue

                    label = cells[0].get_text(strip=True)
                    value_text = cells[-2].get_text(strip=True) if len(cells) >= 3 else (cells[-1].get_text(strip=True) if len(cells) >= 2 else "")

                    # 자산총계
                    if re.search(r"^자산총계", label) and "total_assets" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value:
                            result["total_assets"] = value
                            metadata["parsing_details"]["total_assets"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  자산총계 발견: {value:,}")

                    # 유동자산
                    if re.search(r"^유동자산", label) and "current_assets" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value:
                            result["current_assets"] = value
                            metadata["parsing_details"]["current_assets"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  유동자산 발견: {value:,}")

                    # 부채총계
                    if re.search(r"^부채총계", label) and "total_liabilities" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value:
                            result["total_liabilities"] = value
                            metadata["parsing_details"]["total_liabilities"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  부채총계 발견: {value:,}")

                    # 유동부채
                    if re.search(r"^유동부채", label) and "current_liabilities" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value:
                            result["current_liabilities"] = value
                            metadata["parsing_details"]["current_liabilities"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  유동부채 발견: {value:,}")

                    # 자본총계
                    if re.search(r"^자본총계", label) and "total_equity" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value:
                            result["total_equity"] = value
                            metadata["parsing_details"]["total_equity"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  자본총계 발견: {value:,}")

                    # 재고자산
                    if re.search(r"재고자산", label) and "inventories" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value:
                            result["inventories"] = value
                            metadata["parsing_details"]["inventories"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  재고자산 발견: {value:,}")

                # 주요 항목을 모두 찾았으면 중단
                required_keys = ["total_assets", "total_liabilities", "total_equity",
                                 "current_assets", "current_liabilities", "inventories"]
                if all(k in result for k in required_keys):
                    break

        except Exception as e:
            logger.debug(f"재무상태표 파싱 오류: {e}")

        return result, metadata

    def _parse_cash_flow_xml(self, soup) -> tuple[dict, dict]:
        """
        현금흐름표 XML 파싱

        Returns:
            (data, metadata) 튜플
        """
        result = {}
        metadata = {"parsing_details": {}, "unit_conversion": {}}
        try:
            import re

            # DART XML에서 "현금흐름표" 제목을 포함하는 P 태그 찾기
            title_pattern = re.compile(r"연결현금흐름표|현금흐름표", re.IGNORECASE)

            table_unit = None

            for p_tag in soup.find_all("P"):
                p_text = p_tag.get_text(strip=True)

                if not title_pattern.search(p_text):
                    continue

                # 요약/상세표/주석/영향 제외
                if any(kw in p_text for kw in ["요약", "상세", "주석", "영향", "변경"]):
                    continue

                logger.debug(f"현금흐름표 섹션 발견: {p_text}")

                # 제목이 번호로 시작하면 우선순위 높음
                is_primary_section = bool(re.match(r'^[①②③④⑤가나다라①-⑨]\.?\s', p_text))

                # 이 P 태그 다음의 TABLE 찾기
                table = None

                # 1차: siblings, 2차: 모든 다음 요소
                next_elem = p_tag
                for _ in range(15):
                    next_elem = next_elem.find_next_sibling() if next_elem else None
                    if not next_elem:
                        break
                    if next_elem.name == "TABLE":
                        rows = next_elem.find_all("TR")
                        min_rows = 5 if is_primary_section else 10
                        if len(rows) > min_rows:
                            table = next_elem
                            logger.debug(f"  → 데이터 테이블 발견 (sibling), 행 수: {len(rows)}")
                            break

                if not table:
                    current = p_tag
                    for _ in range(30):
                        current = current.find_next("TABLE")
                        if not current:
                            break
                        rows = current.find_all("TR")
                        min_rows = 5 if is_primary_section else 10
                        if len(rows) > min_rows:
                            table = current
                            logger.debug(f"  → 데이터 테이블 발견 (find_next), 행 수: {len(rows)}")
                            break

                if not table:
                    logger.debug("  → 데이터 테이블을 찾을 수 없음")
                    continue

                # 다중 전략으로 단위 추출
                table_unit, detected_method = self._get_unit_for_table(p_tag, table)
                if table_unit:
                    logger.info(f"현금흐름표 단위 감지: {table_unit} (방법: {detected_method})")
                    metadata["unit_conversion"]["table_unit"] = table_unit
                    metadata["unit_conversion"]["detected_method"] = detected_method
                else:
                    logger.warning("현금흐름표 단위 미감지 → 휴리스틱 사용")
                    metadata["unit_conversion"]["detected_method"] = detected_method

                for row in table.find_all("TR"):
                    cells = row.find_all(["TD", "TH", "TU", "TE"])
                    if len(cells) < 2:
                        continue

                    label = cells[0].get_text(strip=True)
                    value_text = cells[-2].get_text(strip=True) if len(cells) >= 3 else (cells[-1].get_text(strip=True) if len(cells) >= 2 else "")

                    # 영업활동현금흐름
                    if re.search(r"영업활동.*현금흐름", label) and "operating_cash_flow" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value is not None:
                            result["operating_cash_flow"] = value
                            metadata["parsing_details"]["operating_cash_flow"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  영업활동현금흐름 발견: {value:,}")

                    # 투자활동현금흐름
                    if re.search(r"투자활동.*현금흐름", label) and "investing_cash_flow" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value is not None:
                            result["investing_cash_flow"] = value
                            metadata["parsing_details"]["investing_cash_flow"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  투자활동현금흐름 발견: {value:,}")

                    # 재무활동현금흐름
                    if re.search(r"재무활동.*현금흐름", label) and "financing_cash_flow" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value is not None:
                            result["financing_cash_flow"] = value
                            metadata["parsing_details"]["financing_cash_flow"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  재무활동현금흐름 발견: {value:,}")

                    # CAPEX (유형자산의 취득)
                    if re.search(r"유형자산.*취득", label) and "capex" not in result:
                        value = self._parse_amount(value_text, table_unit)
                        if value is not None:
                            result["capex"] = value
                            metadata["parsing_details"]["capex"] = {
                                "method": "regex_match",
                                "pattern": label,
                                "confidence": "high"
                            }
                            logger.debug(f"  CAPEX (유형자산 취득) 발견: {value:,}")

                # 모두 찾았으면 중단
                required_keys = ["operating_cash_flow", "investing_cash_flow", "financing_cash_flow", "capex"]
                if all(k in result for k in required_keys):
                    break

        except Exception as e:
            logger.debug(f"현금흐름표 파싱 오류: {e}")

        return result, metadata

    def _extract_unit_from_table(self, table) -> str | None:
        """
        테이블 헤더에서 단위 추출

        Args:
            table: BeautifulSoup 테이블 객체

        Returns:
            단위 문자열 ("백만원", "천원", "원") 또는 None

        Examples:
            "매출액(단위: 백만원)" → "백만원"
            "(단위:백만원)" → "백만원"
            "단위:원" → "원"
        """
        import re

        # 테이블의 모든 헤더 행(TH, TD)에서 단위 찾기
        for elem in table.find_all(["TH", "TD"]):
            text = elem.get_text(strip=True)
            # 정규식 (완화): 괄호/콜론 선택적
            match = re.search(r'\(?\s*단위\s*[:：]?\s*(백만원|천원|원)\s*\)?', text, re.IGNORECASE)
            if match:
                unit = match.group(1)
                logger.debug(f"테이블 헤더에서 단위 추출: '{unit}' (원문: '{text}')")
                return unit

        return None

    def _extract_unit_from_section(self, p_tag, table) -> str | None:
        """
        섹션 제목(P 태그)과 테이블 사이에서 단위 추출

        Args:
            p_tag: 섹션 제목 P 태그
            table: BeautifulSoup 테이블 객체

        Returns:
            단위 문자열 ("백만원", "천원", "원") 또는 None

        Examples:
            "1. 손익계산서 (단위: 백만원)" → "백만원"
            "가. 재무상태표 (단위 : 천원)" → "천원"
            "(단위:원)" → "원"
        """
        import re

        # 1. P 태그 자체에서 단위 찾기
        p_text = p_tag.get_text(strip=True)
        match = re.search(r'\(?\s*단위\s*[:：]?\s*(백만원|천원|원)\s*\)?', p_text, re.IGNORECASE)
        if match:
            unit = match.group(1)
            logger.debug(f"P 태그에서 단위 추출: '{unit}' (원문: '{p_text}')")
            return unit

        # 2. P와 TABLE 사이의 모든 요소 검색 (최대 5개)
        current = p_tag
        for _ in range(5):
            current = current.find_next_sibling()
            if not current:
                break
            if current == table:
                break  # 테이블 도달

            text = current.get_text(strip=True)
            if not text:
                continue

            match = re.search(r'\(?\s*단위\s*[:：]?\s*(백만원|천원|원)\s*\)?', text, re.IGNORECASE)
            if match:
                unit = match.group(1)
                logger.debug(f"P-TABLE 사이 요소에서 단위 추출: '{unit}' (원문: '{text}')")
                return unit

        return None

    def _get_unit_for_table(self, p_tag, table) -> tuple[str | None, str]:
        """
        다중 전략으로 테이블 단위 추출

        Args:
            p_tag: 섹션 제목 P 태그
            table: BeautifulSoup 테이블 객체

        Returns:
            (단위 문자열, 감지 방법) 튜플
            감지 방법: "header_parse", "section_parse", "none"
        """
        # 1차: 테이블 헤더에서 (기존 로직)
        unit = self._extract_unit_from_table(table)
        if unit:
            logger.info(f"단위 감지: 테이블 헤더 → {unit}")
            return unit, "header_parse"

        # 2차: P 태그와 테이블 사이
        unit = self._extract_unit_from_section(p_tag, table)
        if unit:
            logger.info(f"단위 감지: 섹션 설명 → {unit}")
            return unit, "section_parse"

        # 3차: 실패
        logger.warning("단위 미감지 → 휴리스틱 사용")
        return None, "heuristic"

    def _normalize_to_krw(self, value: int, unit: str | None) -> tuple[int, str]:
        """
        단위를 원(KRW)으로 통일

        Args:
            value: 파싱된 숫자 값
            unit: 단위 문자열 ("백만원", "천원", "원") 또는 None

        Returns:
            (원 단위 값, 사용된 방법) 튜플
            방법: "header_parse" (헤더에서 추출) 또는 "heuristic" (휴리스틱)
        """
        multipliers = {"백만원": 1_000_000, "천원": 1_000, "원": 1}

        if unit and unit in multipliers:
            # 명시적 단위가 있으면 사용
            return value * multipliers[unit], "header_parse"
        else:
            # Fallback: 휴리스틱 (기존 로직)
            # 값 < 100,000,000 (1억) → 백만원으로 간주
            if abs(value) < 100_000_000:
                logger.debug(
                    f"단위 휴리스틱 적용: {value:,} < 1억 → 백만원으로 간주 → {value * 1_000_000:,}원"
                )
                return value * 1_000_000, "heuristic_million"
            else:
                logger.debug(f"단위 휴리스틱 적용: {value:,} ≥ 1억 → 원/천원으로 간주")
                return value, "heuristic_original"

    def _parse_amount(self, text: str, table_unit: str | None = None) -> int | None:
        """
        금액 문자열 파싱 (원 단위로 통일)

        Args:
            text: 금액 문자열 (예: "1,234,567", "(123)", "-")
            table_unit: 테이블 헤더에서 추출한 단위 (선택)

        Returns:
            파싱된 금액 (원 단위) 또는 None

        Note:
            우선순위:
            1. table_unit이 주어지면 명시적 변환
            2. 없으면 휴리스틱 (< 1억 → × 1,000,000)
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
                    value = -int("".join(numbers))
                    normalized_value, _ = self._normalize_to_krw(value, table_unit)
                    return normalized_value

            # 일반 숫자 추출
            numbers = re.findall(r"-?\d+", cleaned)
            if numbers:
                value = int(numbers[0])
                normalized_value, _ = self._normalize_to_krw(value, table_unit)
                return normalized_value

            return None

        except (ValueError, TypeError):
            return None

# 편의 함수
def get_dart_web_financials(corp_code: str, year: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """
    DART API로 재무제표 직접 조회 (OpenDartReader fallback)

    OpenDartReader의 finstate_all이 실패하는 경우,
    list로 사업보고서를 찾아서 fnlttSinglAcnt API로 직접 조회합니다.

    Args:
        corp_code: DART 기업코드
        year: 회계연도

    Returns:
        (재무 데이터, 메타데이터) 튜플
        실패 시 (None, {})
    """
    scraper = DARTWebScraper()

    # 1. 사업보고서 찾기
    rcpNo = scraper.get_annual_report_rcpno(corp_code, year)
    if not rcpNo:
        return None, {}

    # 2. 재무제표 추출
    return scraper.get_financials_from_report(corp_code, year, rcpNo)
