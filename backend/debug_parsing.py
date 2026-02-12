"""
현대지에프홀딩스 2024 연간 재무제표 파싱 테스트
- DataFrame은 정상 반환되는데 parse_financial_data()가 NULL을 반환하는지 확인
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.data_sources.dart_client import DARTClient
from app.config import settings

async def debug_parsing():
    """파싱 로직 디버그"""

    corp_code = '00105280'  # 현대지에프홀딩스
    year = 2024

    print("=" * 80)
    print(f"현대지에프홀딩스 {year}년 연간 재무제표 파싱 테스트")
    print("=" * 80)

    client = DARTClient(settings.dart_api_key)

    # 1. DART API 호출
    print(f"\n[1] DART API 호출")
    df = client.get_financial_statements(corp_code, year, 'annual')

    if df is None or df.empty:
        print("❌ DataFrame이 비어있습니다.")
        return

    print(f"✅ DataFrame 크기: {len(df)} rows")

    # 2. 파싱
    print(f"\n[2] parse_financial_data() 호출")
    data = client.parse_financial_data(df)

    print(f"\n파싱 결과:")
    print("-" * 80)

    fields = [
        'revenue', 'operating_income', 'net_income',
        'total_assets', 'total_liabilities', 'total_equity',
        'current_assets', 'current_liabilities', 'inventories',
        'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
        'capex'
    ]

    for field in fields:
        value = data.get(field)
        if value is None:
            status = "❌ NULL"
        else:
            # 조원 단위로 표시
            trillion = value / 1e12
            status = f"✅ {trillion:>8.2f}조원 ({value:,}원)"
        print(f"  {field:25s}: {status}")

    # 3. raw_data_json 확인
    print(f"\n[3] raw_data_json 메타데이터:")
    if 'raw_data_json' in data:
        import json
        print(json.dumps(data['raw_data_json'], indent=2, ensure_ascii=False))
    else:
        print("  ❌ raw_data_json 없음")

    # 4. DataFrame에서 직접 확인
    print(f"\n[4] DataFrame에서 직접 태그 확인:")

    print("\n  [current_assets]")
    ca_rows = df[df['account_id'] == 'ifrs-full_CurrentAssets']
    if len(ca_rows) > 0:
        for _, row in ca_rows.iterrows():
            print(f"    - sj_div: {row['sj_div']}, account_nm: {row['account_nm']}, thstrm_amount: {row['thstrm_amount']}")
    else:
        print("    ❌ 없음")

    print("\n  [current_liabilities]")
    cl_rows = df[df['account_id'] == 'ifrs-full_CurrentLiabilities']
    if len(cl_rows) > 0:
        for _, row in cl_rows.iterrows():
            print(f"    - sj_div: {row['sj_div']}, account_nm: {row['account_nm']}, thstrm_amount: {row['thstrm_amount']}")
    else:
        print("    ❌ 없음")

    print("\n  [inventories]")
    inv_rows = df[df['account_id'] == 'ifrs-full_Inventories']
    if len(inv_rows) > 0:
        for _, row in inv_rows.iterrows():
            print(f"    - sj_div: {row['sj_div']}, account_nm: {row['account_nm']}, thstrm_amount: {row['thstrm_amount']}")
    else:
        print("    ❌ 없음")

    print("\n  [operating_cash_flow]")
    ocf_rows = df[df['account_id'] == 'ifrs-full_CashFlowsFromUsedInOperatingActivities']
    if len(ocf_rows) > 0:
        for _, row in ocf_rows.iterrows():
            print(f"    - sj_div: {row['sj_div']}, account_nm: {row['account_nm']}, thstrm_amount: {row['thstrm_amount']}")
    else:
        print("    ❌ 없음")

    # 5. _try_parse_strategy 직접 테스트
    print(f"\n[5] _try_parse_strategy() 직접 테스트:")

    # current_assets 전략
    from app.data_sources.dart_client import _ACCOUNT_MAP

    print("\n  [current_assets 전략]")
    for i, strategy in enumerate(_ACCOUNT_MAP['current_assets'], 1):
        result = client._try_parse_strategy(df, strategy)
        print(f"    전략 {i} ({strategy.get('description', 'N/A')}): ", end="")
        if result is None:
            print("❌ NULL")
        else:
            print(f"✅ {result / 1e12:.2f}조원")

    print("\n  [operating_cash_flow 전략]")
    for i, strategy in enumerate(_ACCOUNT_MAP['operating_cash_flow'], 1):
        result = client._try_parse_strategy(df, strategy)
        print(f"    전략 {i} ({strategy.get('description', 'N/A')}): ", end="")
        if result is None:
            print("❌ NULL")
        else:
            print(f"✅ {result / 1e12:.2f}조원")

    print("\n" + "=" * 80)
    print("분석 완료!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_parsing())
