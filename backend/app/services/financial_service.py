"""
재무데이터 수집 서비스

DART에서 재무제표를 수집하여 DB에 저장합니다.
증분 업데이트 방식으로 이미 있는 데이터는 스킵합니다.
"""
import logging
from datetime import datetime
from typing import Set, Tuple

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.data_sources.dart_client import DARTClient
from app.data_sources.stock_client import StockClient
from app.db.models import FinancialStatement
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


async def get_existing_statements(company_id: int) -> Set[Tuple[int, int]]:
    """
    DB에 이미 저장된 재무데이터 목록을 조회합니다.

    Args:
        company_id: Company.id

    Returns:
        Set of (fiscal_year, fiscal_quarter) tuples
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(FinancialStatement.fiscal_year, FinancialStatement.fiscal_quarter)
            .where(FinancialStatement.company_id == company_id)
        )
        existing = set(result.all())
        logger.info(f"기존 재무데이터: {len(existing)}건 (company_id={company_id})")
        return existing


async def collect_financial_data(
    company_id: int,
    stock_code: str,
    corp_code: str,
    force_update: bool = False
) -> dict:
    """
    재무제표 증분 수집

    Args:
        company_id: Company.id
        stock_code: 종목코드
        corp_code: DART 기업코드
        force_update: True면 기존 데이터 덮어쓰기

    Returns:
        {"success": bool, "collected": int, "skipped": int, "failed": int}
    """
    dart_client = DARTClient()
    current_year = datetime.now().year
    current_month = datetime.now().month

    collected = 0
    skipped = 0
    failed = 0

    # 기존 데이터 확인
    existing = set() if force_update else await get_existing_statements(company_id)

    # 수집 대상 결정
    targets = []

    # 1. 연간 실적 (최근 6년)
    # 현재 연도와 다음 연도는 아직 사업보고서가 없을 수 있으므로
    # 여유있게 8년치를 시도하고 성공한 것만 저장 (최대 6년치)
    for year in range(current_year - 7, current_year + 1):
        if (year, 4) not in existing:
            targets.append((year, 4, "annual"))

    # 2. 분기 실적 (최근 8개 분기)
    # 현재 분기 계산
    current_quarter = (current_month - 1) // 3 + 1

    # 최근 분기 생성 (Q4 제외하므로 더 많이 탐색)
    quarters = []
    year = current_year
    quarter = current_quarter
    count = 0

    # 8개의 분기 데이터를 찾을 때까지 또는 최대 15개 분기를 탐색
    for _ in range(15):
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1

        # 4분기는 연간 실적이므로 제외
        if quarter != 4:
            quarters.append((year, quarter))
            count += 1
            if count >= 8:
                break

    # 분기 실적 타겟 추가
    for year, quarter in quarters:
        if (year, quarter) not in existing:
            report_type_map = {
                1: "quarter1",
                2: "quarter2",
                3: "quarter3"
            }
            targets.append((year, quarter, report_type_map[quarter]))

    logger.info(
        f"재무데이터 수집 시작: {stock_code} "
        f"(총 {len(targets)}건, 기존 {len(existing)}건)"
    )

    # DART에서 수집
    for year, quarter, report_type in targets:
        try:
            logger.info(f"수집 중: {stock_code} {year}년 {quarter}분기 ({report_type})")

            # DART API 호출
            df = dart_client.get_financial_statements(
                corp_code=corp_code,
                year=year,
                report_type=report_type
            )

            if df is None or df.empty:
                logger.warning(f"데이터 없음: {stock_code} {year}년 {quarter}분기")
                failed += 1
                continue

            # 재무 데이터 파싱
            data = dart_client.parse_financial_data(df)

            if not data:
                logger.warning(f"파싱 실패: {stock_code} {year}년 {quarter}분기")
                failed += 1
                continue

            # DB 저장
            await save_financial_statement(
                company_id=company_id,
                fiscal_year=year,
                fiscal_quarter=quarter,
                report_type="annual" if quarter == 4 else "quarterly",
                data=data
            )

            collected += 1
            logger.info(
                f"저장 완료: {stock_code} {year}년 {quarter}분기 "
                f"(매출액: {data.get('revenue', 0):,}원)"
            )

        except Exception as e:
            logger.error(
                f"수집 실패: {stock_code} {year}년 {quarter}분기 - {e}",
                exc_info=True
            )
            failed += 1

    skipped = len(existing) if not force_update else 0

    logger.info(
        f"재무데이터 수집 완료: {stock_code} "
        f"(수집: {collected}, 스킵: {skipped}, 실패: {failed})"
    )

    # PER/PBR 수집 (pykrx)
    try:
        await update_per_pbr(company_id, stock_code)
    except Exception as e:
        logger.error(f"PER/PBR 수집 실패: {stock_code} - {e}", exc_info=True)

    return {
        "success": True,
        "collected": collected,
        "skipped": skipped,
        "failed": failed
    }


async def save_financial_statement(
    company_id: int,
    fiscal_year: int,
    fiscal_quarter: int,
    report_type: str,
    data: dict,
    metadata: dict = None
):
    """
    재무제표 데이터를 DB에 저장 (upsert)

    Args:
        company_id: Company.id
        fiscal_year: 회계연도
        fiscal_quarter: 분기 (1-4)
        report_type: "annual" 또는 "quarterly"
        data: 파싱된 재무 데이터
        metadata: 메타데이터 (추정 여부 등)
    """
    async with async_session_factory() as session:
        stmt = pg_insert(FinancialStatement).values(
            company_id=company_id,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            report_type=report_type,
            revenue=data.get("revenue"),
            operating_income=data.get("operating_income"),
            net_income=data.get("net_income"),
            total_assets=data.get("total_assets"),
            total_liabilities=data.get("total_liabilities"),
            total_equity=data.get("total_equity"),
            current_assets=data.get("current_assets"),
            current_liabilities=data.get("current_liabilities"),
            inventories=data.get("inventories"),
            operating_cash_flow=data.get("operating_cash_flow"),
            investing_cash_flow=data.get("investing_cash_flow"),
            financing_cash_flow=data.get("financing_cash_flow"),
            capex=data.get("capex"),
            dividends_paid=None,  # 현재 파싱 안 됨
            shares_outstanding=None,  # 현재 파싱 안 됨
            raw_data_json=metadata or {}  # 메타데이터 저장
        )

        # Unique constraint 충돌 시 업데이트
        stmt = stmt.on_conflict_do_update(
            index_elements=["company_id", "fiscal_year", "fiscal_quarter"],
            set_={
                "revenue": stmt.excluded.revenue,
                "operating_income": stmt.excluded.operating_income,
                "net_income": stmt.excluded.net_income,
                "total_assets": stmt.excluded.total_assets,
                "total_liabilities": stmt.excluded.total_liabilities,
                "total_equity": stmt.excluded.total_equity,
                "current_assets": stmt.excluded.current_assets,
                "current_liabilities": stmt.excluded.current_liabilities,
                "inventories": stmt.excluded.inventories,
                "operating_cash_flow": stmt.excluded.operating_cash_flow,
                "investing_cash_flow": stmt.excluded.investing_cash_flow,
                "financing_cash_flow": stmt.excluded.financing_cash_flow,
                "capex": stmt.excluded.capex,
                "raw_data_json": stmt.excluded.raw_data_json,
            }
        )

        await session.execute(stmt)
        await session.commit()


# 분기별 종료일 (월, 일)
_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


async def update_per_pbr(company_id: int, stock_code: str):
    """
    DB의 재무데이터에 대해 pykrx에서 PER/PBR를 수집하여 업데이트합니다.
    각 분기의 종료일 기준 가장 가까운 거래일의 PER/PBR를 사용합니다.
    """
    # DB에서 기존 재무데이터의 (year, quarter) 목록 조회
    async with async_session_factory() as session:
        result = await session.execute(
            select(FinancialStatement.fiscal_year, FinancialStatement.fiscal_quarter)
            .where(FinancialStatement.company_id == company_id)
        )
        periods = result.all()

    if not periods:
        return

    # 분기별 종료일 계산
    period_dates: dict[tuple[int, int], str] = {}
    for year, quarter in periods:
        month, day = _QUARTER_END[quarter]
        period_dates[(year, quarter)] = f"{year}{month:02d}{day:02d}"

    min_date = min(period_dates.values())
    max_date = max(period_dates.values())

    # pykrx에서 전체 범위의 펀더멘털 데이터 조회 (단일 API 호출)
    stock_client = StockClient()
    fund_df = stock_client.get_fundamentals_range(stock_code, min_date, max_date)

    if fund_df is None or fund_df.empty:
        logger.warning(f"PER/PBR 수집 실패: {stock_code} - 펀더멘털 데이터 없음")
        return

    # 각 기간의 종료일 이하 가장 가까운 거래일의 PER/PBR 추출
    updates: dict[tuple[int, int], dict] = {}
    for (year, quarter), date_str in period_dates.items():
        target_dt = pd.Timestamp(date_str)
        valid_dates = fund_df.index[fund_df.index <= target_dt]
        if len(valid_dates) == 0:
            continue

        row = fund_df.loc[valid_dates[-1]]
        set_clause = {}

        per_val = row.get("PER")
        if pd.notna(per_val) and float(per_val) > 0:
            set_clause["per"] = float(per_val)

        pbr_val = row.get("PBR")
        if pd.notna(pbr_val) and float(pbr_val) > 0:
            set_clause["pbr"] = float(pbr_val)

        if set_clause:
            updates[(year, quarter)] = set_clause

    # DB 업데이트
    async with async_session_factory() as session:
        for (year, quarter), set_clause in updates.items():
            await session.execute(
                update(FinancialStatement)
                .where(
                    FinancialStatement.company_id == company_id,
                    FinancialStatement.fiscal_year == year,
                    FinancialStatement.fiscal_quarter == quarter,
                )
                .values(**set_clause)
            )
        await session.commit()

    logger.info(f"PER/PBR 업데이트 완료: {stock_code} ({len(updates)}건)")
