"""
금융지주사/증권사 재무 데이터 재수집 (force_update=True)

문제:
- 초기 수집 시 current_assets, current_liabilities, cash_flow 등이 NULL로 저장됨
- 증분 수집이 "이미 데이터가 있으니 스킵"하여 계속 NULL로 유지됨

해결:
- force_update=True로 모든 데이터 재수집
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.financial_service import collect_financial_data
from sqlalchemy import text
from app.db.session import sync_engine

# 재수집 대상 금융사
COMPANIES = [
    {"id": 17, "stock_code": "005440", "corp_code": "00105280", "name": "현대지에프홀딩스"},
    {"id": 8, "stock_code": "005940", "corp_code": "00164742", "name": "NH투자증권"},
    {"id": 9, "stock_code": "016360", "corp_code": "00164829", "name": "삼성증권"},
]

async def fix_all():
    """모든 금융사 재무 데이터 재수집"""

    print("=" * 80)
    print("금융지주사/증권사 재무 데이터 재수집 (force_update=True)")
    print("=" * 80)

    for company in COMPANIES:
        company_id = company["id"]
        stock_code = company["stock_code"]
        corp_code = company["corp_code"]
        name = company["name"]

        print(f"\n{'=' * 80}")
        print(f"[{name}] (stock_code: {stock_code})")
        print(f"{'=' * 80}")

        # 재수집 전 DB 상태
        print(f"\n[재수집 전] 연간 재무 데이터 (최근 3년):")
        with sync_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        fiscal_year,
                        CASE WHEN revenue IS NULL THEN 'NULL' ELSE ROUND(revenue::numeric / 1e12, 2)::text || '조' END as revenue,
                        CASE WHEN current_assets IS NULL THEN 'NULL' ELSE ROUND(current_assets::numeric / 1e12, 2)::text || '조' END as ca,
                        CASE WHEN current_liabilities IS NULL THEN 'NULL' ELSE ROUND(current_liabilities::numeric / 1e12, 2)::text || '조' END as cl,
                        CASE WHEN operating_cash_flow IS NULL THEN 'NULL' ELSE ROUND(operating_cash_flow::numeric / 1e12, 2)::text || '조' END as ocf
                    FROM financial_statements
                    WHERE company_id = :company_id
                      AND report_type = 'annual'
                      AND fiscal_year >= 2022
                    ORDER BY fiscal_year DESC
                """),
                {"company_id": company_id}
            )

            print(f"{'연도':<6} {'매출액':<12} {'유동자산':<12} {'유동부채':<12} {'영업CF':<12}")
            print("-" * 54)
            for row in result:
                print(f"{row[0]:<6} {row[1]:<12} {row[2]:<12} {row[3]:<12} {row[4]:<12}")

        # 재수집 실행
        print(f"\n[재수집 실행] force_update=True")
        result = await collect_financial_data(
            company_id=company_id,
            stock_code=stock_code,
            corp_code=corp_code,
            force_update=True
        )

        print(f"\n결과: 수집 {result['collected']}건, 스킵 {result['skipped']}건, 실패 {result['failed']}건")

        # 재수집 후 DB 상태
        print(f"\n[재수집 후] 연간 재무 데이터 (최근 3년):")
        with sync_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        fiscal_year,
                        CASE WHEN revenue IS NULL THEN 'NULL' ELSE ROUND(revenue::numeric / 1e12, 2)::text || '조' END as revenue,
                        CASE WHEN current_assets IS NULL THEN 'NULL' ELSE ROUND(current_assets::numeric / 1e12, 2)::text || '조' END as ca,
                        CASE WHEN current_liabilities IS NULL THEN 'NULL' ELSE ROUND(current_liabilities::numeric / 1e12, 2)::text || '조' END as cl,
                        CASE WHEN operating_cash_flow IS NULL THEN 'NULL' ELSE ROUND(operating_cash_flow::numeric / 1e12, 2)::text || '조' END as ocf
                    FROM financial_statements
                    WHERE company_id = :company_id
                      AND report_type = 'annual'
                      AND fiscal_year >= 2022
                    ORDER BY fiscal_year DESC
                """),
                {"company_id": company_id}
            )

            print(f"{'연도':<6} {'매출액':<12} {'유동자산':<12} {'유동부채':<12} {'영업CF':<12}")
            print("-" * 54)
            row_count = 0
            for row in result:
                print(f"{row[0]:<6} {row[1]:<12} {row[2]:<12} {row[3]:<12} {row[4]:<12}")
                row_count += 1

            if row_count == 0:
                print("  (데이터 없음)")

        print(f"\n✅ {name} 재수집 완료!")

    print(f"\n{'=' * 80}")
    print("전체 재수집 완료!")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    asyncio.run(fix_all())
