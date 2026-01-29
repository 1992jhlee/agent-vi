"""
주가 데이터 클라이언트 테스트

삼성전자(005930)로 pykrx 연동을 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import logging
from datetime import datetime, timedelta

from app.data_sources.stock_client import StockClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_get_ohlcv():
    """OHLCV 데이터 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 1: OHLCV 데이터 조회 (최근 30일)")
    print("=" * 80)

    client = StockClient()
    stock_code = "005930"  # 삼성전자

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    df = client.get_ohlcv(
        stock_code=stock_code,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d")
    )

    if df is not None and not df.empty:
        print(f"✓ OHLCV 조회 성공: {len(df)} 일")
        print(f"\n컬럼: {list(df.columns)}")
        print("\n최근 5일 데이터:")
        print(df.tail(5).to_string())
        return True
    else:
        print(f"✗ OHLCV 조회 실패")
        return False


def test_get_market_cap():
    """시가총액 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 2: 시가총액 조회 (최근 30일)")
    print("=" * 80)

    client = StockClient()
    stock_code = "005930"

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    df = client.get_market_cap(
        stock_code=stock_code,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d")
    )

    if df is not None and not df.empty:
        print(f"✓ 시가총액 조회 성공: {len(df)} 일")
        print(f"\n컬럼: {list(df.columns)}")
        print("\n최근 5일 데이터:")
        print(df.tail(5).to_string())
        return True
    else:
        print(f"✗ 시가총액 조회 실패")
        return False


def test_get_recent_price():
    """최근 주가 데이터 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 3: 최근 주가 데이터 조회 (30일)")
    print("=" * 80)

    client = StockClient()
    stock_code = "005930"

    df = client.get_recent_price(stock_code, days=30)

    if df is not None and not df.empty:
        print(f"✓ 최근 주가 조회 성공: {len(df)} 일")
        print(f"\n컬럼: {list(df.columns)}")
        print("\n최근 5일 데이터:")
        print(df.tail(5).to_string())

        # 통계 출력
        print("\n주가 통계:")
        print(f"  - 평균 종가: {df['close'].mean():,.0f}원")
        print(f"  - 최고가: {df['high'].max():,.0f}원")
        print(f"  - 최저가: {df['low'].min():,.0f}원")
        print(f"  - 현재가: {df['close'].iloc[-1]:,.0f}원")

        return True
    else:
        print(f"✗ 최근 주가 조회 실패")
        return False


def test_get_fundamental_data():
    """펀더멘털 데이터 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 4: 펀더멘털 데이터 조회")
    print("=" * 80)

    client = StockClient()
    stock_code = "005930"

    # 최근 영업일 (오늘 또는 어제)
    date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    fundamental = client.get_fundamental_data(stock_code, date)

    if fundamental:
        print(f"✓ 펀더멘털 데이터 조회 성공:")
        print(f"  - PER: {fundamental.get('per', 'N/A')}")
        print(f"  - PBR: {fundamental.get('pbr', 'N/A')}")
        print(f"  - 배당수익률: {fundamental.get('dividend_yield', 'N/A')}%")
        print(f"  - EPS: {fundamental.get('eps', 'N/A')}")
        print(f"  - BPS: {fundamental.get('bps', 'N/A')}")
        return True
    else:
        print(f"✗ 펀더멘털 데이터 조회 실패")
        return False


def test_get_price_change_rate():
    """수익률 계산 테스트"""
    print("\n" + "=" * 80)
    print("TEST 5: 기간별 수익률 계산")
    print("=" * 80)

    client = StockClient()
    stock_code = "005930"

    change_rates = client.get_price_change_rate(stock_code, days=252)

    if change_rates:
        print(f"✓ 수익률 계산 성공:")
        print(f"  - 1개월: {change_rates.get('1m', 'N/A')}%")
        print(f"  - 3개월: {change_rates.get('3m', 'N/A')}%")
        print(f"  - 6개월: {change_rates.get('6m', 'N/A')}%")
        print(f"  - 1년: {change_rates.get('1y', 'N/A')}%")
        return True
    else:
        print(f"✗ 수익률 계산 실패")
        return False


def test_get_52week_high_low():
    """52주 최고가/최저가 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 6: 52주 최고가/최저가 조회")
    print("=" * 80)

    client = StockClient()
    stock_code = "005930"

    result = client.get_52week_high_low(stock_code)

    if result:
        print(f"✓ 52주 최고가/최저가 조회 성공:")
        print(f"  - 현재가: {result['current_price']:,}원")
        print(f"  - 52주 최고가: {result['week_52_high']:,}원")
        print(f"  - 52주 최저가: {result['week_52_low']:,}원")
        print(f"  - 최고가 대비: {result['high_ratio']:.2f}%")
        print(f"  - 최저가 대비: {result['low_ratio']:.2f}%")
        return True
    else:
        print(f"✗ 52주 최고가/최저가 조회 실패")
        return False


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 80)
    print("주가 데이터 클라이언트 통합 테스트")
    print("대상 기업: 삼성전자 (005930)")
    print("=" * 80)

    # TEST 1: OHLCV
    test_get_ohlcv()

    # TEST 2: 시가총액
    test_get_market_cap()

    # TEST 3: 최근 주가
    test_get_recent_price()

    # TEST 4: 펀더멘털
    test_get_fundamental_data()

    # TEST 5: 수익률
    test_get_price_change_rate()

    # TEST 6: 52주 최고/최저
    test_get_52week_high_low()

    print("\n" + "=" * 80)
    print("✓ 모든 테스트 완료")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)
        print(f"\n❌ 테스트 실패: {e}")
