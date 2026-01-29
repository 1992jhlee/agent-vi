"""
DART 클라이언트 테스트

삼성전자(005930)로 DART API 연동을 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import logging

from app.data_sources.dart_client import DARTClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_get_corp_code():
    """종목코드로 DART 기업코드 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 1: 종목코드로 DART 기업코드 조회")
    print("=" * 80)

    client = DARTClient()
    stock_code = "005930"  # 삼성전자

    corp_code = client.get_corp_code_by_stock_code(stock_code)

    if corp_code:
        print(f"✓ 종목코드 {stock_code}의 DART 기업코드: {corp_code}")
        return corp_code
    else:
        print(f"✗ 기업코드 조회 실패")
        return None


def test_get_company_info(corp_code: str):
    """기업 개황 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 2: 기업 개황 조회")
    print("=" * 80)

    client = DARTClient()

    company_info = client.get_company_info(corp_code)

    if company_info:
        print(f"✓ 기업명: {company_info.get('corp_name', 'N/A')}")
        print(f"  업종: {company_info.get('induty_code', 'N/A')}")
        print(f"  대표자: {company_info.get('ceo_nm', 'N/A')}")
        print(f"  홈페이지: {company_info.get('hm_url', 'N/A')}")
        return True
    else:
        print(f"✗ 기업 개황 조회 실패")
        return False


def test_get_financial_statements(corp_code: str):
    """재무제표 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 3: 재무제표 조회 (2023년 연간)")
    print("=" * 80)

    client = DARTClient()

    # 2023년 사업보고서
    df = client.get_financial_statements(
        corp_code=corp_code,
        year=2023,
        report_type="annual"
    )

    if df is not None and not df.empty:
        print(f"✓ 재무제표 조회 성공: {len(df)} 행")
        print(f"\n컬럼: {list(df.columns)}")

        # 주요 계정과목 샘플 출력
        sample_accounts = ["자산총계", "매출액", "당기순이익"]
        print("\n주요 계정과목:")

        for account in sample_accounts:
            rows = df[df["account_nm"].str.contains(account, case=False, na=False)]
            if not rows.empty:
                value = rows.iloc[0].get("thstrm_amount", "N/A")
                print(f"  - {account}: {value}")

        # 파싱 테스트
        print("\n" + "-" * 80)
        print("재무 데이터 파싱 테스트:")
        print("-" * 80)

        parsed = client.parse_financial_data(df)

        if parsed:
            print("✓ 파싱 성공:")
            for key, value in parsed.items():
                if value:
                    print(f"  - {key}: {value:,}")
        else:
            print("✗ 파싱 실패")

        return True
    else:
        print(f"✗ 재무제표 조회 실패")
        return False


def test_search_disclosures(corp_code: str):
    """공시 검색 테스트"""
    print("\n" + "=" * 80)
    print("TEST 4: 공시 검색 (최근 3개월)")
    print("=" * 80)

    client = DARTClient()

    from datetime import datetime, timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    df = client.search_disclosures(
        corp_code=corp_code,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        max_count=5
    )

    if df is not None and not df.empty:
        print(f"✓ 공시 검색 성공: {len(df)} 건\n")

        for idx, row in df.iterrows():
            print(f"{idx + 1}. [{row.get('rcept_dt', 'N/A')}] {row.get('report_nm', 'N/A')}")

        return True
    else:
        print(f"✗ 공시 검색 실패")
        return False


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 80)
    print("DART 클라이언트 통합 테스트")
    print("대상 기업: 삼성전자 (005930)")
    print("=" * 80)

    # TEST 1: 기업코드 조회
    corp_code = test_get_corp_code()
    if not corp_code:
        print("\n❌ 기업코드 조회 실패. 테스트 중단.")
        return

    # TEST 2: 기업 개황
    test_get_company_info(corp_code)

    # TEST 3: 재무제표
    test_get_financial_statements(corp_code)

    # TEST 4: 공시 검색
    test_search_disclosures(corp_code)

    print("\n" + "=" * 80)
    print("✓ 모든 테스트 완료")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)
        print(f"\n❌ 테스트 실패: {e}")
