"""
HD현재중공업 CAPEX 진단 스크립트

대상: HD현재중공업 (stock_code="329200")
목적: 연간 재무제표에서 CAPEX 관련 행 전체를 연도별로 ダンプ하여
      (1) 기본 태그 매칭 여부
      (2) fallback 태그 매칭 여부
      (3) fs_div/sj_div 조합별 thstrm_amount 값
     을 확인합니다.

실행:
    docker exec -it agent-vi-backend-1 python diagnose_capex.py
  또는 로컬:
    cd backend && python diagnose_capex.py
"""

import sys
import logging
from pathlib import Path

# 백엔드 패키지 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.data_sources.dart_client import DARTClient, _ACCOUNT_MAP, _CAPEX_DETAIL_TAGS  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("diagnose_capex")

# ---------------------------------------------------------------------------
TARGET_STOCK_CODE = "329180"          # HD현대중공업
YEARS_TO_CHECK   = range(2019, 2026)  # 2019~2025 연간

PRIMARY_CAPEX_TAG = _ACCOUNT_MAP["capex"][0]
ALL_CAPEX_TAGS    = {PRIMARY_CAPEX_TAG} | set(_CAPEX_DETAIL_TAGS)

# account_nm 부분 매칭 키워드 (알려진 tag 밖의 후보 발견용)
_CAPEX_KEYWORDS = ["purchase", "취득", "설비", "capex", "자본적지출", "유형자산", "건설중인"]
# ---------------------------------------------------------------------------


def _extract_value_debug(value) -> tuple:
    """_extract_value와 동일한 변환 로직 + 과정 설명 반환."""
    original = repr(value)
    try:
        if isinstance(value, str):
            stripped = value.replace(",", "")
            if not stripped:
                return None, f"{original} → strip → 빈문자열 → None"
            result = int(float(stripped))
            return result, f"{original} → {result}"
        elif isinstance(value, (int, float)):
            return int(value), f"{original} → {int(value)}"
        return None, f"{original} → 지원안됨(type={type(value).__name__}) → None"
    except (ValueError, TypeError) as e:
        return None, f"{original} → EXCEPTION: {e} → None"


def diagnose_year(client: DARTClient, corp_code: str, year: int) -> dict:
    """단일 연도의 진단을 실행."""
    df = client.get_financial_statements(corp_code=corp_code, year=year, report_type="annual")

    if df is None or df.empty:
        return {"year": year, "error": "DART 응답 없음"}

    cf_mask = df["sj_div"] == "CF"

    result = {
        "year": year,
        "df_row_count": len(df),
        "cf_row_count": int(cf_mask.sum()),
        "fs_div_values": list(df["fs_div"].unique()) if "fs_div" in df.columns else ["COLUMN_MISSING"],
    }

    # --- CAPEX 후보 행 수집 ---
    candidates = []

    # (1) 알려진 tag로 정확 매칭
    tag_mask = df["account_id"].isin(ALL_CAPEX_TAGS) & cf_mask
    for _, row in df[tag_mask].iterrows():
        val, trace = _extract_value_debug(row.get("thstrm_amount", ""))
        candidates.append({
            "source": "TAG_MATCH",
            "is_primary": row["account_id"] == PRIMARY_CAPEX_TAG,
            "fs_div": row.get("fs_div", "N/A"),
            "account_id": row["account_id"],
            "account_nm": row.get("account_nm", ""),
            "raw": repr(row.get("thstrm_amount", "")),
            "value": val,
            "trace": trace,
        })

    # (2) account_nm 키워드로 추가 후보 탐색
    for _, row in df[cf_mask].iterrows():
        if row["account_id"] in ALL_CAPEX_TAGS:
            continue
        nm = str(row.get("account_nm", "")).lower()
        if any(kw in nm for kw in _CAPEX_KEYWORDS):
            val, trace = _extract_value_debug(row.get("thstrm_amount", ""))
            candidates.append({
                "source": "KEYWORD_MATCH",
                "is_primary": False,
                "fs_div": row.get("fs_div", "N/A"),
                "account_id": row["account_id"],
                "account_nm": row.get("account_nm", ""),
                "raw": repr(row.get("thstrm_amount", "")),
                "value": val,
                "trace": trace,
            })

    result["candidates"] = candidates

    # --- 현재 생산 로직 시뮬레이션 (iloc[0]만 본 결과) ---
    primary_rows = df[(df["account_id"] == PRIMARY_CAPEX_TAG) & cf_mask]
    if primary_rows.empty:
        result["primary_status"] = "NOT_FOUND"
    else:
        first_val, _ = _extract_value_debug(primary_rows.iloc[0].get("thstrm_amount", 0))
        if first_val is not None:
            result["primary_status"] = f"OK (value={first_val})"
        else:
            # iloc[0] 이후 행에서 값 탐색 → BUG 직접 확인
            bug_row_idx = None
            for i in range(1, len(primary_rows)):
                alt_val, _ = _extract_value_debug(primary_rows.iloc[i].get("thstrm_amount", 0))
                if alt_val is not None:
                    bug_row_idx = i
                    fs = primary_rows.iloc[i].get("fs_div", "?")
                    result["primary_status"] = (
                        f"BUG CONFIRMED: iloc[0]=None, iloc[{i}] fs_div={fs} value={alt_val}"
                    )
                    break
            if bug_row_idx is None:
                result["primary_status"] = "TAG_FOUND_ALL_VALUES_NONE"

    # --- fallback 시뮬레이션 ---
    fb_sum, fb_found = 0, False
    for tag in _CAPEX_DETAIL_TAGS:
        rows = df[(df["account_id"] == tag) & cf_mask]
        if not rows.empty:
            val, _ = _extract_value_debug(rows.iloc[0].get("thstrm_amount", 0))
            if val is not None:
                fb_sum += val
                fb_found = True
    result["fallback_status"] = f"SUM={fb_sum}" if fb_found else "NOT_FOUND"

    return result


def print_report(diagnostics: list):
    divider = "─" * 90

    print("\n" + "=" * 90)
    print(f"  HD현재중공업 CAPEX 진단 보고서  (종목코드: {TARGET_STOCK_CODE})")
    print("=" * 90)

    for d in diagnostics:
        print(f"\n{divider}")
        year = d["year"]
        print(f"  [{year}년]  행수={d.get('df_row_count','?')}  "
              f"CF행수={d.get('cf_row_count','?')}  "
              f"fs_div={d.get('fs_div_values','?')}")
        print(divider)

        if "error" in d:
            print(f"  ERROR: {d['error']}")
            continue

        print(f"  Primary : {d.get('primary_status', 'N/A')}")
        print(f"  Fallback: {d.get('fallback_status', 'N/A')}")

        for i, c in enumerate(d.get("candidates", [])):
            flag = " <<<" if c["value"] is None else ""
            print(f"    #{i+1} [{c['source']:<12}] "
                  f"fs_div={str(c['fs_div']):>4}  "
                  f"tag={c['account_id']}")
            print(f"         nm='{c['account_nm']}'"
                  f"  raw={c['raw']} → value={c['value']}{flag}")

        if not d.get("candidates"):
            print("    (후보 행 없음)")

    # --- 요약 테이블 ---
    print(f"\n{'=' * 90}")
    print("  요약")
    print(f"{'=' * 90}")
    print(f"  {'연도':>6} | {'Primary 결과':<50} | {'Fallback':<15}")
    print(f"  {'─'*6}-+-{'─'*50}-+-{'─'*15}")
    for d in diagnostics:
        p = d.get("primary_status", d.get("error", "?"))
        f = d.get("fallback_status", "?")
        print(f"  {d['year']:>6} | {p:<50} | {f:<15}")
    print()


def main():
    client = DARTClient()

    corp_code = client.get_corp_code_by_stock_code(TARGET_STOCK_CODE)
    if not corp_code:
        logger.error(f"corp_code 조회 실패: stock_code={TARGET_STOCK_CODE}")
        sys.exit(1)
    print(f"corp_code: {corp_code}")

    diagnostics = []
    for year in YEARS_TO_CHECK:
        print(f"  진단 중: {year}년 ...")
        diagnostics.append(diagnose_year(client, corp_code, year))

    print_report(diagnostics)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단됨")
    except Exception as e:
        logger.error(f"실행 오류: {e}", exc_info=True)
        sys.exit(1)
