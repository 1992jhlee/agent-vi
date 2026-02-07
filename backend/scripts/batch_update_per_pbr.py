#!/usr/bin/env python3
"""
모든 종목의 PER/PBR을 일괄 갱신합니다.

Usage:
    python scripts/batch_update_per_pbr.py [--stock-code 005930]
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.models import Company
from app.db.session import async_session_factory
from app.services.financial_service import update_per_pbr


async def update_all_stocks(stock_code: str = None):
    """
    모든 종목 또는 특정 종목의 PER/PBR을 갱신합니다.

    Args:
        stock_code: 특정 종목코드 (None이면 전체)
    """
    async with async_session_factory() as session:
        query = select(Company.id, Company.stock_code, Company.company_name)

        if stock_code:
            query = query.where(Company.stock_code == stock_code)
        else:
            query = query.order_by(Company.stock_code)

        result = await session.execute(query)
        companies = result.all()

    if not companies:
        print(f"종목을 찾을 수 없습니다: {stock_code if stock_code else '전체'}")
        return

    total = len(companies)
    print(f"\n{'='*60}")
    print(f"PER/PBR 일괄 갱신 시작: {total}개 종목")
    print(f"{'='*60}\n")

    success = 0
    failed = 0

    for idx, (company_id, stock_code, company_name) in enumerate(companies, 1):
        print(f"[{idx}/{total}] {stock_code} {company_name}")
        print("-" * 60)

        try:
            await update_per_pbr(company_id, stock_code)
            success += 1
            print(f"✓ 완료\n")
        except Exception as e:
            failed += 1
            print(f"✗ 실패: {e}\n")

    print(f"\n{'='*60}")
    print(f"갱신 완료: 성공 {success}개, 실패 {failed}개")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="PER/PBR 일괄 갱신")
    parser.add_argument(
        "--stock-code",
        type=str,
        help="특정 종목코드만 갱신 (생략 시 전체)"
    )
    args = parser.parse_args()

    asyncio.run(update_all_stocks(args.stock_code))


if __name__ == "__main__":
    main()
