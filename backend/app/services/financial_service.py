"""
재무데이터 수집 서비스

DART에서 재무제표를 수집하여 DB에 저장합니다.
증분 업데이트 방식으로 이미 있는 데이터는 스킵합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Set, Tuple

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.data_sources.dart_client import DARTClient
from app.data_sources.stock_client import StockClient
from app.data_sources.dart_web_scraper import get_dart_web_financials
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

            # 현금흐름표는 DART가 누적으로 제공하므로 단독 실적으로 변환
            # 손익계산서는 이미 단독, 재무상태표는 시점 기준이므로 변환 불필요
            if quarter != 4:  # 분기 데이터만 (Q4는 연간이므로 나중에 처리)
                data = await convert_cashflow_to_standalone(
                    company_id=company_id,
                    fiscal_year=year,
                    fiscal_quarter=quarter,
                    cumulative_data=data
                )

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

    # 4Q 단독 실적 생성 (연간 - 3Q)
    await generate_q4_standalone_statements(company_id, stock_code)

    skipped = len(existing) if not force_update else 0

    logger.info(
        f"재무데이터 수집 완료: {stock_code} "
        f"(수집: {collected}, 스킵: {skipped}, 실패: {failed})"
    )

    # 다중 소스 fallback (DART 실패한 연간 데이터만)
    if failed > 0:
        fallback_collected = await try_multi_source_fallback(company_id, stock_code, corp_code, targets)
        if fallback_collected > 0:
            collected += fallback_collected
            failed -= fallback_collected
            logger.info(f"Fallback으로 {fallback_collected}건 추가 수집")

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
            index_elements=["company_id", "fiscal_year", "fiscal_quarter", "report_type"],
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
    DB의 재무데이터에 대해 PER/PBR를 계산하여 업데이트합니다.

    - PBR: 모든 기간에서 시가총액 / total_equity로 직접 계산 (잔액 기반)
    - PER (Q4/연간): 시가총액 / net_income으로 직접 계산 (당해연도 실적 기반)
    - PER (Q1-Q3): pykrx trailing PER 사용 (누적 실적으로 단순 연산 불가)

    에러가 발생해도 부분적으로 계산 가능한 데이터는 저장합니다.
    """
    try:
        # DB에서 재무데이터와 필요한 컬럼 조회 (report_type 포함)
        async with async_session_factory() as session:
            result = await session.execute(
                select(
                    FinancialStatement.fiscal_year,
                    FinancialStatement.fiscal_quarter,
                    FinancialStatement.report_type,
                    FinancialStatement.net_income,
                    FinancialStatement.total_equity,
                    FinancialStatement.pbr,
                )
                .where(FinancialStatement.company_id == company_id)
            )
            rows = result.all()

        if not rows:
            logger.warning(f"재무데이터 없음: {stock_code}")
            return
    except Exception as e:
        logger.error(f"재무데이터 조회 실패: {stock_code} - {e}", exc_info=True)
        return

    # 분기별 종료일 및 재무 실적 매핑 (report_type별로 구분)
    period_dates: dict[tuple[int, int, str], str] = {}
    period_financials: dict[tuple[int, int, str], dict] = {}
    for year, quarter, report_type, net_income, total_equity, existing_pbr in rows:
        month, day = _QUARTER_END[quarter]
        key = (year, quarter, report_type)
        period_dates[key] = f"{year}{month:02d}{day:02d}"
        period_financials[key] = {
            "net_income": net_income,
            "total_equity": total_equity,
            "existing_pbr": existing_pbr,  # 기존 DB의 PBR
        }

    # 필요한 날짜 목록 생성 (분기 종료일만)
    dates_to_fetch = list(period_dates.values())

    # 데이터 소스 초기화
    stock_client = StockClient()
    public_client = _get_public_data_client()

    # 시가총액 배치 조회 (금융위원회 → pykrx fallback)
    market_data = {}
    try:
        market_data = _get_market_cap_batch_with_fallback(
            stock_code,
            dates_to_fetch,
            public_client,
            stock_client
        )
        if market_data:
            logger.info(f"시가총액 조회 성공: {stock_code} ({len(market_data)}/{len(dates_to_fetch)}건)")
        else:
            logger.warning(f"시가총액 데이터 없음: {stock_code} — PER/PBR 계산 제한적")
    except Exception as e:
        logger.error(f"시가총액 조회 실패: {stock_code} - {e}", exc_info=True)

    updates: dict[tuple[int, int, str], dict] = {}

    for (year, quarter, report_type), date_str in period_dates.items():
        net_income = period_financials[(year, quarter, report_type)]["net_income"]
        total_equity = period_financials[(year, quarter, report_type)]["total_equity"]
        set_clause = {}

        # 시가총액 기반 계산은 데이터가 있을 때만
        data = market_data.get(date_str)
        if data and data.get("market_cap"):
            market_cap = data["market_cap"]

            # PER: Q4 annual만 연간 실적 기준으로 직접 계산 (이미 누적 순이익)
            if quarter == 4 and report_type == "annual" and net_income is not None and net_income != 0:
                set_clause["per"] = market_cap / net_income

            # PBR: 모든 기간에서 시가총액 / total_equity
            if total_equity is not None and total_equity > 0:
                set_clause["pbr"] = market_cap / total_equity

        if set_clause:
            updates[(year, quarter, report_type)] = set_clause

    # Q1-Q4의 PER 계산 (quarterly만 대상, 누적 순이익 기반)
    quarterly_periods = [(y, q, rt) for y, q, rt in period_dates if rt == "quarterly"]
    if quarterly_periods:
        # 누적 순이익 기반 PER 계산
        # - 1Q: Q1 * 4
        # - 2Q: (Q1 + Q2) * 2
        # - 3Q: (Q1 + Q2 + Q3) * 4/3
        # - 4Q: (Q1 + Q2 + Q3 + Q4) * 1 = 연간 누적
        for key in quarterly_periods:
            year, quarter, report_type = key
            date_str = period_dates[key]
            data = market_data.get(date_str)

            if data and data.get("market_cap"):
                market_cap = data["market_cap"]

                # 해당 분기까지의 누적 순이익 계산
                cumulative_income = 0
                quarters_found = 0

                for q in range(1, quarter + 1):
                    q_key = (year, q, "quarterly")
                    if q_key in period_financials:
                        q_income = period_financials[q_key]["net_income"]
                        if q_income is not None:
                            cumulative_income += q_income
                            quarters_found += 1

                # 누적 순이익이 있고, 필요한 분기가 모두 존재하는 경우만 계산
                if quarters_found == quarter and cumulative_income != 0:
                    # 연환산: 누적 순이익 * (4 / 분기수)
                    annualized_income = cumulative_income * (4 / quarter)
                    calculated_per = market_cap / annualized_income

                    updates.setdefault(key, {})["per"] = calculated_per
                    logger.info(
                        f"{stock_code} {year}Q{quarter} PER (누적): {calculated_per:.2f} "
                        f"(시총: {market_cap:,.0f}, 누적순이익: {cumulative_income:,.0f}, "
                        f"연환산: {annualized_income:,.0f})"
                    )
                elif quarters_found < quarter:
                    logger.warning(
                        f"{stock_code} {year}Q{quarter} PER 계산 불가: "
                        f"이전 분기 데이터 부족 ({quarters_found}/{quarter})"
                    )

        # 2차 fallback: 시가총액도 없으면 PBR과 자본총계에서 시가총액 역산 후 PER 계산
        # PBR은 이미 계산되어 updates에 있거나 기존 DB에 있을 수 있음
        for key in quarterly_periods:
            year, quarter, report_type = key
            # 이미 PER가 있으면 스킵
            if key in updates and "per" in updates[key]:
                continue

            total_equity = period_financials[key]["total_equity"]

            # PBR 우선순위: 1) updates에 새로 계산된 값, 2) 기존 DB 값
            pbr = updates.get(key, {}).get("pbr")
            if not pbr:
                pbr = period_financials[key].get("existing_pbr")

            if pbr and total_equity and total_equity > 0:
                # 해당 분기까지의 누적 순이익 계산
                cumulative_income = 0
                quarters_found = 0

                for q in range(1, quarter + 1):
                    q_key = (year, q, "quarterly")
                    if q_key in period_financials:
                        q_income = period_financials[q_key]["net_income"]
                        if q_income is not None:
                            cumulative_income += q_income
                            quarters_found += 1

                # 누적 순이익이 있고, 필요한 분기가 모두 존재하는 경우만 계산
                if quarters_found == quarter and cumulative_income != 0:
                    # PBR = 시가총액 / 자본총계 → 시가총액 = PBR * 자본총계
                    market_cap = pbr * total_equity
                    # 연환산: 누적 순이익 * (4 / 분기수)
                    annualized_income = cumulative_income * (4 / quarter)
                    calculated_per = market_cap / annualized_income

                    updates.setdefault(key, {})["per"] = calculated_per
                    logger.info(
                        f"{stock_code} {year}Q{quarter} PER PBR역산(누적): {calculated_per:.2f} "
                        f"(PBR: {pbr:.2f}, 자본: {total_equity:,.0f}, "
                        f"누적순이익: {cumulative_income:,.0f}, 연환산: {annualized_income:,.0f})"
                    )

    # DB 업데이트 (각 기간별로 개별 트랜잭션으로 처리하여 부분 실패 허용)
    success_count = 0
    fail_count = 0

    for key, set_clause in updates.items():
        year, quarter, report_type = key
        try:
            async with async_session_factory() as session:
                await session.execute(
                    update(FinancialStatement)
                    .where(
                        FinancialStatement.company_id == company_id,
                        FinancialStatement.fiscal_year == year,
                        FinancialStatement.fiscal_quarter == quarter,
                        FinancialStatement.report_type == report_type,
                    )
                    .values(**set_clause)
                )
                await session.commit()
                success_count += 1
        except Exception as e:
            logger.error(
                f"DB 업데이트 실패: {stock_code} {year}Q{quarter} ({report_type}) - {e}",
                exc_info=True
            )
            fail_count += 1

    # NULL 원인 로깅 (PER/PBR이 업데이트되지 않은 기간)
    updated_periods = set(updates.keys())
    all_periods = set(period_dates.keys())
    null_periods = all_periods - updated_periods

    if null_periods:
        null_details = []
        for key in sorted(null_periods):
            year, quarter, report_type = key
            net_income = period_financials[key]["net_income"]
            total_equity = period_financials[key]["total_equity"]
            date_str = period_dates[key]
            has_market_cap = date_str in market_data

            reasons = []
            if not has_market_cap:
                reasons.append("시가총액 없음")
            if net_income is None or net_income <= 0:
                reasons.append(f"순이익 {'없음' if net_income is None else '음수/0'}")
            if total_equity is None or total_equity <= 0:
                reasons.append("자본총계 없음/음수")

            null_details.append(f"{year}Q{quarter}/{report_type}({', '.join(reasons)})")

        logger.info(
            f"PER/PBR NULL 유지: {stock_code} {len(null_periods)}건 - {', '.join(null_details)}"
        )

    logger.info(
        f"PER/PBR 업데이트 완료: {stock_code} "
        f"(성공: {success_count}, 실패: {fail_count}, NULL: {len(null_periods)})"
    )


def _get_public_data_client():
    """
    금융위원회 공공데이터 API 클라이언트 생성

    Returns:
        PublicDataClient 또는 None (서비스 키 미설정 시)
    """
    from app.config import settings
    from app.data_sources.public_data_client import PublicDataClient

    if not settings.public_data_service_key:
        logger.info("PUBLIC_DATA_SERVICE_KEY 미설정 - 금융위원회 API 사용 불가")
        return None

    return PublicDataClient(settings.public_data_service_key)


def _get_market_cap_batch_with_fallback(
    stock_code: str,
    dates: list[str],
    public_client,
    stock_client: StockClient
) -> dict[str, dict]:
    """
    시가총액 배치 조회 (금융위원회 → pykrx fallback)

    Args:
        stock_code: 종목코드
        dates: 조회할 날짜 리스트 (YYYYMMDD 형식)
        public_client: PublicDataClient 또는 None
        stock_client: StockClient

    Returns:
        {"20240630": {"market_cap": 123..., ...}, ...}
    """
    results = {}

    # 1차: 금융위원회 API
    if public_client:
        try:
            results = public_client.get_market_cap_batch(stock_code, dates)
            if results:
                logger.info(
                    f"✓ 시가총액: 금융위원회 ({stock_code}, {len(results)}/{len(dates)}건)"
                )
                # 전부 성공하면 바로 반환
                if len(results) == len(dates):
                    return results
        except Exception as e:
            logger.warning(f"금융위원회 API 실패: {e} → pykrx fallback")

    # 2차: pykrx (실패한 날짜만)
    missing_dates = [d for d in dates if d not in results]
    if missing_dates:
        try:
            # 최소/최대 날짜 범위로 조회
            min_date = min(missing_dates)
            max_date = max(missing_dates)

            # 휴장일 대응: 앞 45일, 뒤 7일 여유 (연말 특별 휴장 대응)
            min_date_dt = datetime.strptime(min_date, "%Y%m%d")
            max_date_dt = datetime.strptime(max_date, "%Y%m%d")

            start = (min_date_dt - timedelta(days=45)).strftime("%Y%m%d")
            end = (max_date_dt + timedelta(days=7)).strftime("%Y%m%d")

            cap_df = stock_client.get_market_cap(stock_code, start, end)

            if cap_df is not None and not cap_df.empty:
                for date_str in missing_dates:
                    target_dt = pd.Timestamp(date_str)
                    valid_dates = cap_df.index[cap_df.index <= target_dt]

                    if len(valid_dates) > 0:
                        market_cap = cap_df.loc[valid_dates[-1], "market_cap"]
                        if pd.notna(market_cap) and float(market_cap) > 0:
                            results[date_str] = {
                                "market_cap": float(market_cap),
                                "date": date_str
                            }

                logger.info(
                    f"✓ 시가총액: pykrx fallback ({stock_code}, "
                    f"{len([d for d in missing_dates if d in results])}건)"
                )

        except Exception as e:
            logger.error(f"pykrx fallback 실패: {e}")

    return results


async def convert_cashflow_to_standalone(
    company_id: int,
    fiscal_year: int,
    fiscal_quarter: int,
    cumulative_data: dict
) -> dict:
    """
    현금흐름표 항목을 누적에서 단독 실적으로 변환합니다.

    DART는 현금흐름표를 연초부터 누적으로 제공하므로:
    - 1Q: 누적 = 단독 (변환 불필요)
    - 2Q: 누적 - 1Q 누적 = 2Q 단독
    - 3Q: 누적 - 2Q 누적 = 3Q 단독

    손익계산서는 DART가 이미 단독으로 제공하므로 변환하지 않습니다.
    재무상태표는 시점 기준이므로 변환 개념이 없습니다.

    Args:
        company_id: Company.id
        fiscal_year: 회계연도
        fiscal_quarter: 분기 (1, 2, 3)
        cumulative_data: DART에서 파싱한 누적 데이터

    Returns:
        단독 실적으로 변환된 데이터
    """
    data = cumulative_data.copy()

    # 1분기는 누적 = 단독이므로 변환 불필요
    if fiscal_quarter == 1:
        return data

    # 이전 분기 데이터 조회
    prev_quarter = fiscal_quarter - 1

    async with async_session_factory() as session:
        result = await session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.company_id == company_id,
                FinancialStatement.fiscal_year == fiscal_year,
                FinancialStatement.fiscal_quarter == prev_quarter
            )
        )
        prev_statement = result.scalar_one_or_none()

    if not prev_statement:
        logger.warning(
            f"이전 분기 데이터 없음: {fiscal_year}/{prev_quarter}Q - "
            f"현금흐름 단독 변환 불가, 누적 값 사용"
        )
        return data

    # 현금흐름표 항목만 단독으로 변환 (손익, 재무상태는 그대로)
    cf_fields = ["operating_cash_flow", "investing_cash_flow", "financing_cash_flow", "capex"]

    for field in cf_fields:
        if field in data and data[field] is not None:
            prev_value = getattr(prev_statement, field, None)
            if prev_value is not None:
                data[field] = data[field] - prev_value
                logger.debug(
                    f"{fiscal_year}/{fiscal_quarter}Q {field} 단독 변환: "
                    f"누적 {cumulative_data[field]:,} - 이전분기 {prev_value:,} = {data[field]:,}"
                )

    return data


async def generate_q4_standalone_statements(company_id: int, stock_code: str):
    """
    연간 데이터와 3Q 데이터를 이용하여 4Q 단독 실적을 생성합니다.

    4분기는 별도 보고서가 없고 사업보고서(연간)만 있으므로:
    - 4Q 단독 손익 = 연간 - 3Q 누적 (DART 손익은 이미 단독이므로 3Q까지 합산 필요)
    - 4Q 단독 현금흐름 = 연간 - 3Q 누적
    - 재무상태표는 연간 값 그대로 사용 (시점 기준)

    Args:
        company_id: Company.id
        stock_code: 종목코드
    """
    async with async_session_factory() as session:
        # 연간 데이터 조회 (report_type='annual')
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

            # 동일 연도 3Q 데이터 조회
            result_q3 = await session.execute(
                select(FinancialStatement)
                .where(
                    FinancialStatement.company_id == company_id,
                    FinancialStatement.fiscal_year == year,
                    FinancialStatement.fiscal_quarter == 3,
                    FinancialStatement.report_type == "quarterly"
                )
            )
            q3_statement = result_q3.scalar_one_or_none()

            if not q3_statement:
                logger.warning(f"{year}년 3Q 데이터 없음 - 4Q 단독 생성 불가")
                continue

            # 동일 연도 1Q, 2Q 데이터도 조회 (손익 합산용)
            result_q1_q2 = await session.execute(
                select(FinancialStatement)
                .where(
                    FinancialStatement.company_id == company_id,
                    FinancialStatement.fiscal_year == year,
                    FinancialStatement.fiscal_quarter.in_([1, 2]),
                    FinancialStatement.report_type == "quarterly"
                )
                .order_by(FinancialStatement.fiscal_quarter)
            )
            q1_q2_statements = result_q1_q2.scalars().all()

            # 1Q, 2Q, 3Q가 모두 있는지 확인
            quarters_present = {stmt.fiscal_quarter for stmt in q1_q2_statements}
            quarters_present.add(3)  # 3Q는 이미 확인됨

            if quarters_present != {1, 2, 3}:
                missing = {1, 2, 3} - quarters_present
                logger.warning(
                    f"{year}년 4Q 단독 생성 불가: {missing} 분기 데이터 누락 - "
                    f"1Q, 2Q, 3Q가 모두 있어야 정확한 계산 가능"
                )
                continue

            # 손익계산서는 DART가 단독으로 제공하므로 1Q+2Q+3Q 합산
            q1_q2_q3_sum = {}
            income_fields = ["revenue", "operating_income", "net_income"]

            for field in income_fields:
                total = 0
                for stmt in [*q1_q2_statements, q3_statement]:
                    value = getattr(stmt, field, None)
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

                # 재무상태표: 연간 값 그대로 (시점 기준)
                "total_assets": annual.total_assets,
                "total_liabilities": annual.total_liabilities,
                "total_equity": annual.total_equity,
                "current_assets": annual.current_assets,
                "current_liabilities": annual.current_liabilities,
                "inventories": annual.inventories,

                # 현금흐름: 연간 - 3Q 누적
                "operating_cash_flow": (
                    (annual.operating_cash_flow - q3_statement.operating_cash_flow)
                    if (annual.operating_cash_flow and q3_statement.operating_cash_flow)
                    else None
                ),
                "investing_cash_flow": (
                    (annual.investing_cash_flow - q3_statement.investing_cash_flow)
                    if (annual.investing_cash_flow and q3_statement.investing_cash_flow)
                    else None
                ),
                "financing_cash_flow": (
                    (annual.financing_cash_flow - q3_statement.financing_cash_flow)
                    if (annual.financing_cash_flow and q3_statement.financing_cash_flow)
                    else None
                ),
                "capex": (
                    (annual.capex - q3_statement.capex)
                    if (annual.capex and q3_statement.capex)
                    else None
                ),
            }

            # 4Q 단독 실적 저장 (fiscal_quarter=4, report_type="quarterly")
            await save_financial_statement(
                company_id=company_id,
                fiscal_year=year,
                fiscal_quarter=4,
                report_type="quarterly",
                data=q4_data
            )

            revenue_str = f"{q4_data.get('revenue'):,}원" if q4_data.get('revenue') else "N/A"
            logger.info(
                f"4Q 단독 실적 생성: {stock_code} {year}/4Q "
                f"(매출액: {revenue_str})"
            )

async def try_multi_source_fallback(
    company_id: int,
    stock_code: str,
    corp_code: str,
    targets: list[tuple[int, int, str]]
) -> int:
    """
    DART 웹 크롤링으로 DART API 실패한 연간 데이터 수집

    OpenDartReader의 list 메서드와 fnlttSinglAcnt API를 사용하여
    DART API(finstate_all)가 제공하지 않는 과거 재무제표를 가져옵니다.

    Args:
        company_id: Company.id
        stock_code: 종목코드
        corp_code: DART 기업코드
        targets: DART API에서 시도했던 (year, quarter, report_type) 목록

    Returns:
        성공적으로 수집한 건수
    """
    # 연간 데이터만 시도 (quarter=4, report_type="annual")
    annual_years = [
        year for year, quarter, report_type in targets
        if quarter == 4 and report_type == "annual"
    ]

    if not annual_years:
        return 0

    collected = 0

    # DART API 실패한 각 연도에 대해 웹 크롤링 시도
    for year in annual_years:
        try:
            # DART 웹 크롤링
            logger.info(f"DART 웹 크롤링 시도: {stock_code} {year}년")
            data = get_dart_web_financials(corp_code, year)

            # 데이터가 있으면 저장
            if data and any(data.values()):
                await save_financial_statement(
                    company_id=company_id,
                    fiscal_year=year,
                    fiscal_quarter=4,
                    report_type="annual",
                    data=data,
                    metadata={"source": "dart_web", "fallback": True}
                )

                collected += 1
                revenue_str = f"{data.get('revenue'):,}원" if data.get('revenue') else "N/A"
                logger.info(
                    f"DART 웹 크롤링 저장: {stock_code} {year}년 (매출액: {revenue_str})"
                )
            else:
                logger.warning(f"DART 웹 크롤링 실패: {stock_code} {year}년 - 데이터를 얻을 수 없습니다")

        except Exception as e:
            logger.error(f"Fallback 오류: {stock_code} {year}년 - {e}", exc_info=True)
            continue

    if collected > 0:
        logger.info(f"Fallback 수집 완료: {stock_code} (총 {collected}건)")

    return collected
