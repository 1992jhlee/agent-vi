"""
모든 회사의 재무 데이터를 force_update=True로 전체 재수집

목적:
- 과거 잘못 저장된 데이터 정리
- 최신 파싱 로직으로 모든 데이터 재수집
- 증분 수집으로 인한 누락 데이터 해결
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.services.financial_service import collect_financial_data
from sqlalchemy import text
from app.db.session import sync_engine

async def force_update_all():
    """전체 회사 재무 데이터 force_update"""

    # 전체 회사 목록 조회
    with sync_engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, stock_code, company_name, corp_code
                FROM companies
                WHERE is_active = true
                ORDER BY id
            """)
        )
        companies = [dict(row._mapping) for row in result]

    total = len(companies)
    print("=" * 100)
    print(f"전체 재무 데이터 강제 재수집 (force_update=True)")
    print(f"대상: {total}개 회사")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    success_count = 0
    failed_companies = []

    for idx, company in enumerate(companies, 1):
        company_id = company["id"]
        stock_code = company["stock_code"]
        company_name = company["company_name"]
        corp_code = company["corp_code"]

        print(f"\n[{idx}/{total}] {company_name} ({stock_code})")
        print("-" * 100)

        try:
            # force_update=True로 재수집
            result = await collect_financial_data(
                company_id=company_id,
                stock_code=stock_code,
                corp_code=corp_code,
                force_update=True
            )

            collected = result.get("collected", 0)
            failed = result.get("failed", 0)

            if result.get("success"):
                success_count += 1
                status = "✅ 성공"
            else:
                status = "⚠️ 부분 성공"
                failed_companies.append(company_name)

            print(f"\n결과: {status}")
            print(f"  - 수집: {collected}건")
            print(f"  - 실패: {failed}건")

            # 수집된 데이터 샘플 확인 (최근 2년 연간)
            with sync_engine.connect() as conn:
                check_result = conn.execute(
                    text("""
                        SELECT
                            fiscal_year,
                            CASE WHEN revenue IS NULL THEN 'NULL' ELSE ROUND(revenue::numeric / 1e12, 2)::text || '조' END as revenue,
                            CASE WHEN current_assets IS NULL THEN 'NULL' ELSE ROUND(current_assets::numeric / 1e12, 2)::text || '조' END as ca,
                            CASE WHEN operating_cash_flow IS NULL THEN 'NULL' ELSE ROUND(operating_cash_flow::numeric / 1e12, 2)::text || '조' END as ocf
                        FROM financial_statements
                        WHERE company_id = :company_id
                          AND report_type = 'annual'
                          AND fiscal_year >= 2023
                        ORDER BY fiscal_year DESC
                        LIMIT 2
                    """),
                    {"company_id": company_id}
                )

                rows = list(check_result)
                if rows:
                    print(f"\n  최근 연간 데이터:")
                    for row in rows:
                        print(f"    {row[0]}년: 매출 {row[1]}, 유동자산 {row[2]}, 영업CF {row[3]}")
                else:
                    print(f"\n  ⚠️ 연간 데이터 없음")

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            failed_companies.append(company_name)
            import traceback
            traceback.print_exc()

        # 진행률 표시
        print(f"\n진행률: {idx}/{total} ({idx/total*100:.1f}%)")

    # 최종 요약
    print("\n" + "=" * 100)
    print("전체 재수집 완료!")
    print("=" * 100)
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n결과:")
    print(f"  - 성공: {success_count}/{total}개 회사")
    print(f"  - 실패: {len(failed_companies)}개 회사")

    if failed_companies:
        print(f"\n실패한 회사:")
        for name in failed_companies:
            print(f"  - {name}")

    # 전체 통계
    print("\n" + "=" * 100)
    print("전체 데이터 통계")
    print("=" * 100)

    with sync_engine.connect() as conn:
        # 연간 데이터 통계
        result = conn.execute(
            text("""
                SELECT
                    c.stock_code,
                    c.company_name,
                    COUNT(*) as total_years,
                    COUNT(CASE WHEN fs.current_assets IS NULL THEN 1 END) as missing_ca,
                    COUNT(CASE WHEN fs.operating_cash_flow IS NULL THEN 1 END) as missing_cf
                FROM companies c
                LEFT JOIN financial_statements fs ON c.id = fs.company_id AND fs.report_type = 'annual'
                WHERE c.is_active = true
                GROUP BY c.id, c.stock_code, c.company_name
                ORDER BY c.stock_code
            """)
        )

        print(f"\n{'종목코드':<10} {'회사명':<20} {'연간 데이터':<12} {'유동자산 누락':<15} {'현금흐름 누락':<15}")
        print("-" * 82)
        for row in result:
            stock_code, company_name, total, missing_ca, missing_cf = row
            ca_status = f"{missing_ca}/{total}" if missing_ca > 0 else "✅"
            cf_status = f"{missing_cf}/{total}" if missing_cf > 0 else "✅"
            print(f"{stock_code:<10} {company_name:<20} {total:<12} {ca_status:<15} {cf_status:<15}")

    print("\n" + "=" * 100)

if __name__ == "__main__":
    asyncio.run(force_update_all())
