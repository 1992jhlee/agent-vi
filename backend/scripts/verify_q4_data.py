#!/usr/bin/env python3
"""
4Q 단독 실적 데이터 검증
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from app.db.models import Company, FinancialStatement
from app.db.session import async_session_factory


async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(Company))
        companies = result.scalars().all()

    print("2024년 분기 재무데이터 검증")
    print("=" * 80)

    for company in companies:
        async with async_session_factory() as session:
            result = await session.execute(
                select(FinancialStatement)
                .where(
                    FinancialStatement.company_id == company.id,
                    FinancialStatement.fiscal_year == 2024
                )
                .order_by(FinancialStatement.fiscal_quarter, FinancialStatement.report_type)
            )
            statements = result.scalars().all()

        if not statements:
            continue

        print(f"\n{company.company_name} ({company.stock_code}):")

        quarterlies = [s for s in statements if s.report_type == 'quarterly']
        annual = next((s for s in statements if s.report_type == 'annual'), None)

        if not quarterlies:
            print("  분기 데이터 없음")
            continue

        for q in quarterlies:
            revenue = q.revenue / 1_000_000_000_000 if q.revenue else None
            if revenue is not None:
                print(f"  {q.fiscal_quarter}Q: {revenue:>8.1f}조")
            else:
                print(f"  {q.fiscal_quarter}Q: None")

        quarterly_sum = sum(s.revenue for s in quarterlies if s.revenue)
        if annual and annual.revenue:
            annual_rev = annual.revenue / 1_000_000_000_000
            print(f"  연간: {annual_rev:>8.1f}조")

            if quarterly_sum:
                sum_rev = quarterly_sum / 1_000_000_000_000
                print(f"  분기합계: {sum_rev:>5.1f}조")
                diff = abs(quarterly_sum - annual.revenue) / 1_000_000_000_000
                if diff < 0.1:
                    print("  ✓ 일치")
                else:
                    print(f"  ⚠️ 차이: {diff:.1f}조")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
