"""
현대지에프홀딩스 연간 재무제표 DART API 응답 분석
- 실제 반환되는 account_id, account_nm 확인
- current_assets, current_liabilities, cash_flow 필드 누락 원인 파악
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.data_sources.dart_client import DARTClient
from app.config import settings
import pandas as pd

async def debug_hyundai_annual():
    """현대지에프홀딩스 2024 연간 DART API 응답 분석"""

    corp_code = '00105280'  # 현대지에프홀딩스
    year = 2024

    print("=" * 80)
    print(f"현대지에프홀딩스 {year}년 연간 재무제표 DART API 응답 분석")
    print("=" * 80)

    client = DARTClient(settings.dart_api_key)

    # DART API 호출
    print(f"\n[1] DART API 호출: corp_code={corp_code}, year={year}, reprt_code='annual'")
    df = client.get_financial_statements(corp_code, year, 'annual')

    if df is None or df.empty:
        print("❌ DataFrame이 비어있습니다.")
        return

    print(f"✅ DataFrame 크기: {len(df)} rows × {len(df.columns)} columns")
    print(f"\n[2] DataFrame 컬럼: {list(df.columns)}\n")

    # 재무상태표 (BS) 분석
    print("=" * 80)
    print("[3] 재무상태표 (BS) 데이터 분석")
    print("=" * 80)

    bs_df = df[df['sj_div'] == 'BS'].copy()
    print(f"\n재무상태표 행 개수: {len(bs_df)}")

    # current_assets 관련 검색
    print("\n--- [유동자산] 관련 항목 검색 ---")

    # 1. 표준 태그 검색
    standard_ca = bs_df[bs_df['account_id'] == 'ifrs-full_CurrentAssets']
    print(f"\n1) 표준 태그 'ifrs-full_CurrentAssets': {len(standard_ca)}개")
    if len(standard_ca) > 0:
        print(standard_ca[['account_id', 'account_nm', 'thstrm_amount']].to_string(index=False))
    else:
        print("   ❌ 없음")

    # 2. 계정과목명에 "유동자산" 포함
    keyword_ca = bs_df[bs_df['account_nm'].str.contains('유동자산', na=False)]
    print(f"\n2) 계정과목명에 '유동자산' 포함: {len(keyword_ca)}개")
    if len(keyword_ca) > 0:
        print(keyword_ca[['account_id', 'account_nm', 'thstrm_amount']].to_string(index=False))
    else:
        print("   ❌ 없음")

    # 3. 총자산, 비유동자산 확인
    print(f"\n3) 총자산 - 비유동자산으로 계산 가능한지 확인")
    total_assets = bs_df[bs_df['account_id'] == 'ifrs-full_Assets']
    noncurrent_assets = bs_df[bs_df['account_id'] == 'ifrs-full_NoncurrentAssets']

    print(f"   총자산 (ifrs-full_Assets): {len(total_assets)}개")
    if len(total_assets) > 0:
        print(total_assets[['account_id', 'account_nm', 'thstrm_amount']].head().to_string(index=False))

    print(f"\n   비유동자산 (ifrs-full_NoncurrentAssets): {len(noncurrent_assets)}개")
    if len(noncurrent_assets) > 0:
        print(noncurrent_assets[['account_id', 'account_nm', 'thstrm_amount']].head().to_string(index=False))

    # current_liabilities 관련 검색
    print("\n\n--- [유동부채] 관련 항목 검색 ---")

    # 1. 표준 태그 검색
    standard_cl = bs_df[bs_df['account_id'] == 'ifrs-full_CurrentLiabilities']
    print(f"\n1) 표준 태그 'ifrs-full_CurrentLiabilities': {len(standard_cl)}개")
    if len(standard_cl) > 0:
        print(standard_cl[['account_id', 'account_nm', 'thstrm_amount']].to_string(index=False))
    else:
        print("   ❌ 없음")

    # 2. 계정과목명에 "유동부채" 포함
    keyword_cl = bs_df[bs_df['account_nm'].str.contains('유동부채', na=False)]
    print(f"\n2) 계정과목명에 '유동부채' 포함: {len(keyword_cl)}개")
    if len(keyword_cl) > 0:
        print(keyword_cl[['account_id', 'account_nm', 'thstrm_amount']].to_string(index=False))
    else:
        print("   ❌ 없음")

    # 재고자산 검색
    print("\n\n--- [재고자산] 관련 항목 검색 ---")

    standard_inv = bs_df[bs_df['account_id'] == 'ifrs-full_Inventories']
    print(f"\n1) 표준 태그 'ifrs-full_Inventories': {len(standard_inv)}개")
    if len(standard_inv) > 0:
        print(standard_inv[['account_id', 'account_nm', 'thstrm_amount']].to_string(index=False))
    else:
        print("   ❌ 없음")

    keyword_inv = bs_df[bs_df['account_nm'].str.contains('재고자산', na=False)]
    print(f"\n2) 계정과목명에 '재고자산' 포함: {len(keyword_inv)}개")
    if len(keyword_inv) > 0:
        print(keyword_inv[['account_id', 'account_nm', 'thstrm_amount']].to_string(index=False))

    # 현금흐름표 (CF) 분석
    print("\n\n" + "=" * 80)
    print("[4] 현금흐름표 (CF) 데이터 분석")
    print("=" * 80)

    cf_df = df[df['sj_div'] == 'CF'].copy()
    print(f"\n현금흐름표 행 개수: {len(cf_df)}")

    if len(cf_df) == 0:
        print("❌ 현금흐름표 데이터가 없습니다!")
    else:
        # operating_cash_flow 검색
        print("\n--- [영업활동 현금흐름] 관련 항목 검색 ---")

        standard_ocf = cf_df[cf_df['account_id'] == 'ifrs-full_CashFlowsFromUsedInOperatingActivities']
        print(f"\n1) 표준 태그 'ifrs-full_CashFlowsFromUsedInOperatingActivities': {len(standard_ocf)}개")
        if len(standard_ocf) > 0:
            print(standard_ocf[['account_id', 'account_nm', 'thstrm_amount']].to_string(index=False))
        else:
            print("   ❌ 없음")

        keyword_ocf = cf_df[cf_df['account_nm'].str.contains('영업활동', na=False)]
        print(f"\n2) 계정과목명에 '영업활동' 포함: {len(keyword_ocf)}개")
        if len(keyword_ocf) > 0:
            print(keyword_ocf[['account_id', 'account_nm', 'thstrm_amount']].head(10).to_string(index=False))

        # 대체 태그들 확인
        print(f"\n3) 대체 XBRL 태그 확인")
        alt_tags = [
            'ifrs-full_CashFlowsFromUsedInOperations',
            'dart_CashGeneratedFromUsedInOperations',
            'ifrs-full_IncreaseDecreaseInCashAndCashEquivalents'
        ]
        for tag in alt_tags:
            alt_df = cf_df[cf_df['account_id'] == tag]
            print(f"   {tag}: {len(alt_df)}개")
            if len(alt_df) > 0:
                print(alt_df[['account_id', 'account_nm', 'thstrm_amount']].head(3).to_string(index=False))

    # 비표준 계정코드 사용 현황
    print("\n\n" + "=" * 80)
    print("[5] 비표준 계정코드 ('-표준계정코드 미사용-') 사용 현황")
    print("=" * 80)

    non_standard = df[df['account_id'] == '-표준계정코드 미사용-']
    print(f"\n비표준 계정코드 행 개수: {len(non_standard)}")

    if len(non_standard) > 0:
        # BS 중에서 유동자산/유동부채 관련
        bs_non_std = non_standard[non_standard['sj_div'] == 'BS']
        current_related = bs_non_std[
            bs_non_std['account_nm'].str.contains('유동자산|유동부채|재고자산', na=False)
        ]

        print(f"\n재무상태표 중 유동자산/유동부채/재고자산 관련 비표준 계정: {len(current_related)}개")
        if len(current_related) > 0:
            print(current_related[['sj_div', 'account_nm', 'thstrm_amount']].to_string(index=False))

        # CF 중에서 현금흐름 관련
        cf_non_std = non_standard[non_standard['sj_div'] == 'CF']
        cf_related = cf_non_std[
            cf_non_std['account_nm'].str.contains('영업활동|투자활동|재무활동|현금', na=False)
        ]

        print(f"\n현금흐름표 중 영업/투자/재무활동 관련 비표준 계정: {len(cf_related)}개")
        if len(cf_related) > 0:
            print(cf_related[['sj_div', 'account_nm', 'thstrm_amount']].head(20).to_string(index=False))

    # 전체 account_id 종류 확인
    print("\n\n" + "=" * 80)
    print("[6] 전체 account_id 목록 (각 sj_div별)")
    print("=" * 80)

    for div in ['BS', 'IS', 'CF', 'CIS']:
        div_df = df[df['sj_div'] == div]
        if len(div_df) > 0:
            unique_ids = div_df['account_id'].unique()
            print(f"\n[{div}] 고유 account_id 개수: {len(unique_ids)}")
            print("주요 account_id:")
            for aid in sorted(unique_ids)[:20]:  # 상위 20개만
                count = len(div_df[div_df['account_id'] == aid])
                print(f"  - {aid}: {count}개")

    print("\n\n" + "=" * 80)
    print("분석 완료!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_hyundai_annual())
