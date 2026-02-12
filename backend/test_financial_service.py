"""
financial_service.py의 collect_financial_data를 직접 호출해서 저장 테스트
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.financial_service import collect_financial_data
from sqlalchemy import text
from app.db.session import sync_engine

async def test_collect():
    """현대지에프홀딩스 2024 연간 데이터 수집 테스트"""

    company_id = 17
    stock_code = '005440'
    corp_code = '00105280'

    print("=" * 80)
    print("financial_service.collect_financial_data() 직접 호출 테스트")
    print("=" * 80)

    # 기존 데이터 확인
    print("\n[1] 수집 전 DB 상태:")
    with sync_engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    fiscal_year,
                    fiscal_quarter,
                    report_type,
                    CASE WHEN revenue IS NULL THEN 'NULL' ELSE ROUND(revenue::numeric / 1e12, 2)::text END as revenue_t,
                    CASE WHEN current_assets IS NULL THEN 'NULL' ELSE ROUND(current_assets::numeric / 1e12, 2)::text END as ca_t,
                    CASE WHEN current_liabilities IS NULL THEN 'NULL' ELSE ROUND(current_liabilities::numeric / 1e12, 2)::text END as cl_t,
                    CASE WHEN operating_cash_flow IS NULL THEN 'NULL' ELSE ROUND(operating_cash_flow::numeric / 1e12, 2)::text END as ocf_t
                FROM financial_statements
                WHERE company_id = :company_id
                  AND fiscal_year = 2024
                  AND fiscal_quarter = 4
                ORDER BY report_type
            """),
            {"company_id": company_id}
        )

        print(f"{'Report Type':<12} {'Revenue(조)':<12} {'CA(조)':<12} {'CL(조)':<12} {'OCF(조)':<12}")
        print("-" * 60)
        for row in result:
            print(f"{row[2]:<12} {row[3]:<12} {row[4]:<12} {row[5]:<12} {row[6]:<12}")

    # 수집 실행 (force_update=True로 덮어쓰기)
    print("\n[2] collect_financial_data() 실행 (force_update=True):")
    result = await collect_financial_data(
        company_id=company_id,
        stock_code=stock_code,
        corp_code=corp_code,
        force_update=True  # 기존 데이터 덮어쓰기
    )

    print(f"\n수집 결과:")
    print(f"  - 성공: {result['success']}")
    print(f"  - 수집: {result['collected']}건")
    print(f"  - 스킵: {result['skipped']}건")
    print(f"  - 실패: {result['failed']}건")

    # 수집 후 DB 상태 확인
    print("\n[3] 수집 후 DB 상태:")
    with sync_engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    fiscal_year,
                    fiscal_quarter,
                    report_type,
                    CASE WHEN revenue IS NULL THEN 'NULL' ELSE ROUND(revenue::numeric / 1e12, 2)::text END as revenue_t,
                    CASE WHEN current_assets IS NULL THEN 'NULL' ELSE ROUND(current_assets::numeric / 1e12, 2)::text END as ca_t,
                    CASE WHEN current_liabilities IS NULL THEN 'NULL' ELSE ROUND(current_liabilities::numeric / 1e12, 2)::text END as cl_t,
                    CASE WHEN operating_cash_flow IS NULL THEN 'NULL' ELSE ROUND(operating_cash_flow::numeric / 1e12, 2)::text END as ocf_t
                FROM financial_statements
                WHERE company_id = :company_id
                  AND fiscal_year = 2024
                  AND fiscal_quarter = 4
                ORDER BY report_type
            """),
            {"company_id": company_id}
        )

        print(f"{'Report Type':<12} {'Revenue(조)':<12} {'CA(조)':<12} {'CL(조)':<12} {'OCF(조)':<12}")
        print("-" * 60)
        for row in result:
            print(f"{row[2]:<12} {row[3]:<12} {row[4]:<12} {row[5]:<12} {row[6]:<12}")

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_collect())
