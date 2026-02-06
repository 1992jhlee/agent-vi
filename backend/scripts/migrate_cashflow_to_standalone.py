#!/usr/bin/env python3
"""
현금흐름표 누적 → 단독 실적 마이그레이션 및 4Q 단독 실적 생성

기존 DB의 현금흐름 항목(operating_cash_flow, investing_cash_flow,
financing_cash_flow, capex)을 누적에서 단독 실적으로 변환하고,
4Q 단독 실적 레코드를 생성합니다.

Usage:
    # 드라이런 (변경하지 않고 확인만)
    python scripts/migrate_cashflow_to_standalone.py --dry-run

    # 실제 실행
    python scripts/migrate_cashflow_to_standalone.py

    # 특정 회사만
    python scripts/migrate_cashflow_to_standalone.py --stock-code 005930
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import Company, FinancialStatement
from app.db.session import async_session_factory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def migrate_cashflow_for_company(
    company_id: int,
    stock_code: str,
    company_name: str,
    dry_run: bool = False
) -> dict:
    """
    특정 회사의 현금흐름 데이터를 단독 실적으로 변환합니다.

    Returns:
        {"converted": int, "q4_generated": int}
    """
    converted = 0
    q4_generated = 0

    async with async_session_factory() as session:
        # 모든 분기 데이터 조회 (report_type='quarterly')
        result = await session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.company_id == company_id,
                FinancialStatement.report_type == "quarterly"
            )
            .order_by(
                FinancialStatement.fiscal_year,
                FinancialStatement.fiscal_quarter
            )
        )
        quarterly_statements = result.scalars().all()

        # 연도별로 그룹화
        by_year = {}
        for stmt in quarterly_statements:
            year = stmt.fiscal_year
            if year not in by_year:
                by_year[year] = {}
            by_year[year][stmt.fiscal_quarter] = stmt

        # 2Q, 3Q 현금흐름 변환
        cf_fields = [
            "operating_cash_flow",
            "investing_cash_flow",
            "financing_cash_flow",
            "capex"
        ]

        for year, quarters in by_year.items():
            # 2Q 변환 (2Q 누적 - 1Q 누적)
            if 2 in quarters and 1 in quarters:
                q2_stmt = quarters[2]
                q1_stmt = quarters[1]

                updates = {}
                for field in cf_fields:
                    q2_val = getattr(q2_stmt, field, None)
                    q1_val = getattr(q1_stmt, field, None)
                    if q2_val is not None and q1_val is not None:
                        standalone = q2_val - q1_val
                        updates[field] = standalone
                        logger.debug(
                            f"{stock_code} {year}/2Q {field}: "
                            f"{q2_val:,} - {q1_val:,} = {standalone:,}"
                        )

                if updates and not dry_run:
                    await session.execute(
                        update(FinancialStatement)
                        .where(
                            FinancialStatement.company_id == company_id,
                            FinancialStatement.fiscal_year == year,
                            FinancialStatement.fiscal_quarter == 2,
                            FinancialStatement.report_type == "quarterly"
                        )
                        .values(**updates)
                    )
                    converted += 1

            # 3Q 변환 (3Q 누적 - 2Q 누적)
            if 3 in quarters and 2 in quarters:
                q3_stmt = quarters[3]
                q2_stmt = quarters[2]

                updates = {}
                for field in cf_fields:
                    q3_val = getattr(q3_stmt, field, None)
                    q2_val = getattr(q2_stmt, field, None)
                    if q3_val is not None and q2_val is not None:
                        standalone = q3_val - q2_val
                        updates[field] = standalone
                        logger.debug(
                            f"{stock_code} {year}/3Q {field}: "
                            f"{q3_val:,} - {q2_val:,} = {standalone:,}"
                        )

                if updates and not dry_run:
                    await session.execute(
                        update(FinancialStatement)
                        .where(
                            FinancialStatement.company_id == company_id,
                            FinancialStatement.fiscal_year == year,
                            FinancialStatement.fiscal_quarter == 3,
                            FinancialStatement.report_type == "quarterly"
                        )
                        .values(**updates)
                    )
                    converted += 1

        if not dry_run:
            await session.commit()

    # 4Q 단독 실적 생성
    q4_generated = await generate_q4_for_company(
        company_id, stock_code, company_name, dry_run
    )

    return {"converted": converted, "q4_generated": q4_generated}


async def generate_q4_for_company(
    company_id: int,
    stock_code: str,
    company_name: str,
    dry_run: bool = False
) -> int:
    """
    특정 회사의 4Q 단독 실적을 생성합니다.

    Returns:
        생성된 4Q 레코드 수
    """
    q4_generated = 0

    async with async_session_factory() as session:
        # 연간 데이터 조회
        result = await session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.company_id == company_id,
                FinancialStatement.report_type == "annual"
            )
            .order_by(FinancialStatement.fiscal_year.desc())
        )
        annual_statements = result.scalars().all()

        for annual in annual_statements:
            year = annual.fiscal_year

            # 동일 연도 1Q, 2Q, 3Q 조회
            result_q = await session.execute(
                select(FinancialStatement)
                .where(
                    FinancialStatement.company_id == company_id,
                    FinancialStatement.fiscal_year == year,
                    FinancialStatement.fiscal_quarter.in_([1, 2, 3]),
                    FinancialStatement.report_type == "quarterly"
                )
                .order_by(FinancialStatement.fiscal_quarter)
            )
            quarterly_stmts = result_q.scalars().all()

            # 1Q, 2Q, 3Q가 모두 있어야 4Q 계산 가능
            if len(quarterly_stmts) < 3:
                logger.warning(
                    f"{stock_code} {year}: 분기 데이터 부족 "
                    f"({len(quarterly_stmts)}/3) - 4Q 생성 불가"
                )
                continue

            q_by_num = {stmt.fiscal_quarter: stmt for stmt in quarterly_stmts}
            if not all(q in q_by_num for q in [1, 2, 3]):
                logger.warning(
                    f"{stock_code} {year}: 1Q, 2Q, 3Q 중 일부 누락 - 4Q 생성 불가"
                )
                continue

            # 손익계산서는 단독이므로 1Q+2Q+3Q 합산
            income_fields = ["revenue", "operating_income", "net_income"]
            q1_q2_q3_sum = {}

            for field in income_fields:
                total = 0
                for q in [1, 2, 3]:
                    value = getattr(q_by_num[q], field, None)
                    if value is not None:
                        total += value
                q1_q2_q3_sum[field] = total

            # 4Q 단독 데이터 계산
            q4_data = {
                # 손익: 연간 - (1Q+2Q+3Q)
                "revenue": (
                    (annual.revenue - q1_q2_q3_sum["revenue"])
                    if annual.revenue else None
                ),
                "operating_income": (
                    (annual.operating_income - q1_q2_q3_sum["operating_income"])
                    if annual.operating_income else None
                ),
                "net_income": (
                    (annual.net_income - q1_q2_q3_sum["net_income"])
                    if annual.net_income else None
                ),

                # 재무상태표: 연간 값 그대로
                "total_assets": annual.total_assets,
                "total_liabilities": annual.total_liabilities,
                "total_equity": annual.total_equity,
                "current_assets": annual.current_assets,
                "current_liabilities": annual.current_liabilities,
                "inventories": annual.inventories,

                # 현금흐름: 연간 - 3Q 누적
                "operating_cash_flow": (
                    (annual.operating_cash_flow - q_by_num[3].operating_cash_flow)
                    if (annual.operating_cash_flow and q_by_num[3].operating_cash_flow)
                    else None
                ),
                "investing_cash_flow": (
                    (annual.investing_cash_flow - q_by_num[3].investing_cash_flow)
                    if (annual.investing_cash_flow and q_by_num[3].investing_cash_flow)
                    else None
                ),
                "financing_cash_flow": (
                    (annual.financing_cash_flow - q_by_num[3].financing_cash_flow)
                    if (annual.financing_cash_flow and q_by_num[3].financing_cash_flow)
                    else None
                ),
                "capex": (
                    (annual.capex - q_by_num[3].capex)
                    if (annual.capex and q_by_num[3].capex)
                    else None
                ),
            }

            logger.info(
                f"{stock_code} {year}/4Q 생성: "
                f"매출 {q4_data['revenue']:,}원 (연간 {annual.revenue:,} - 3Q합 {q1_q2_q3_sum['revenue']:,})"
            )

            if not dry_run:
                # 4Q quarterly 레코드가 이미 있는지 확인
                result_existing = await session.execute(
                    select(FinancialStatement).where(
                        FinancialStatement.company_id == company_id,
                        FinancialStatement.fiscal_year == year,
                        FinancialStatement.fiscal_quarter == 4,
                        FinancialStatement.report_type == "quarterly"
                    )
                )
                existing_q4 = result_existing.scalar_one_or_none()

                if existing_q4:
                    # 이미 있으면 업데이트
                    from sqlalchemy import update as sql_update
                    await session.execute(
                        sql_update(FinancialStatement)
                        .where(
                            FinancialStatement.company_id == company_id,
                            FinancialStatement.fiscal_year == year,
                            FinancialStatement.fiscal_quarter == 4,
                            FinancialStatement.report_type == "quarterly"
                        )
                        .values(**q4_data)
                    )
                else:
                    # 없으면 insert (annual과 충돌하지 않도록 명시적으로 quarterly)
                    stmt = pg_insert(FinancialStatement).values(
                        company_id=company_id,
                        fiscal_year=year,
                        fiscal_quarter=4,
                        report_type="quarterly",
                        **q4_data
                    )
                    await session.execute(stmt)

                q4_generated += 1

        if not dry_run:
            await session.commit()

    return q4_generated


async def main(dry_run: bool = False, stock_code: str = None):
    """
    전체 마이그레이션 실행
    """
    logger.info("=" * 60)
    logger.info("현금흐름표 단독 실적 마이그레이션 시작")
    logger.info(f"모드: {'DRY RUN (변경 없음)' if dry_run else '실제 실행'}")
    logger.info("=" * 60)

    async with async_session_factory() as session:
        # 대상 회사 조회
        if stock_code:
            result = await session.execute(
                select(Company).where(Company.stock_code == stock_code)
            )
            companies = result.scalars().all()
            if not companies:
                logger.error(f"종목코드 {stock_code}를 찾을 수 없습니다.")
                return
        else:
            result = await session.execute(select(Company))
            companies = result.scalars().all()

    total_companies = len(companies)
    total_converted = 0
    total_q4_generated = 0

    logger.info(f"\n처리 대상: {total_companies}개 회사\n")

    for idx, company in enumerate(companies, 1):
        logger.info(
            f"[{idx}/{total_companies}] {company.company_name} ({company.stock_code})"
        )

        try:
            result = await migrate_cashflow_for_company(
                company.id,
                company.stock_code,
                company.company_name,
                dry_run
            )
            total_converted += result["converted"]
            total_q4_generated += result["q4_generated"]

            logger.info(
                f"  ✓ 현금흐름 변환: {result['converted']}건, "
                f"4Q 생성: {result['q4_generated']}건"
            )

        except Exception as e:
            logger.error(f"  ✗ 실패: {e}", exc_info=True)

    logger.info("\n" + "=" * 60)
    logger.info("마이그레이션 완료")
    logger.info(f"총 현금흐름 변환: {total_converted}건")
    logger.info(f"총 4Q 생성: {total_q4_generated}건")
    if dry_run:
        logger.info("** DRY RUN 모드였으므로 실제 변경 없음 **")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="현금흐름표 단독 실적 마이그레이션 및 4Q 생성"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제로 변경하지 않고 확인만 합니다"
    )
    parser.add_argument(
        "--stock-code",
        type=str,
        help="특정 종목코드만 처리 (예: 005930)"
    )

    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, stock_code=args.stock_code))
