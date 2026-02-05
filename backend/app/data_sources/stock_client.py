"""
주가 데이터 클라이언트

pykrx를 사용하여 한국 주식시장(KOSPI/KOSDAQ)의 주가 및 시가총액 데이터를 조회합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests as _requests
from pykrx import stock
from pykrx.website.krx.krxio import Post as _KrxPost

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# KRX WAF 우회 패치
# data.krx.co.kr은 www.krx.co.kr의 세션 쿠키(SCOUTER)가 없으면 403을 반환합니다.
# pykrx의 Post 클래스는 세션 없이 raw requests.post()를 사용하므로,
# Post.read를 monkey-patch하여 세션 기반 요청으로 바꾸면 정상 작동합니다.
# ---------------------------------------------------------------------------
_krx_session: _requests.Session | None = None


def _init_krx_session() -> _requests.Session:
    """www.krx.co.kr을 방문하여 SCOUTER 쿠키를 획득하고 세션을 (re)초기화한다."""
    global _krx_session
    _krx_session = _requests.Session()
    _krx_session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    })
    try:
        _krx_session.get("https://www.krx.co.kr/", timeout=10)
        logger.info("KRX 세션 초기화 완료 (SCOUTER cookie 획득)")
    except Exception as e:
        logger.warning(f"KRX 세션 초기화 실패: {e}")
    return _krx_session


def _krx_patched_read(self, **params):
    """세션 기반 POST 요청 — KRX WAF 우회 및 403 시 자동 세션 갱신."""
    global _krx_session
    if _krx_session is None:
        _init_krx_session()
    resp = _krx_session.post(self.url, headers=self.headers, data=params)
    if resp.status_code == 403:
        logger.warning("KRX 403 응답 — 세션 갱신 후 재시도")
        _init_krx_session()
        resp = _krx_session.post(self.url, headers=self.headers, data=params)
    return resp


_KrxPost.read = _krx_patched_read
# ---------------------------------------------------------------------------


class StockClient:
    """pykrx 기반 주가 데이터 클라이언트"""

    def __init__(self):
        logger.info("StockClient 초기화 완료")

    def get_ohlcv(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        adjust_price: bool = True
    ) -> pd.DataFrame | None:
        """
        OHLCV (시가/고가/저가/종가/거래량) 데이터 조회

        Args:
            stock_code: 종목코드 (예: "005930")
            start_date: 시작일 (YYYYMMDD 또는 YYYY-MM-DD)
            end_date: 종료일 (YYYYMMDD 또는 YYYY-MM-DD)
            adjust_price: 수정주가 사용 여부

        Returns:
            OHLCV DataFrame (인덱스: 날짜) 또는 실패 시 None
            컬럼: 시가, 고가, 저가, 종가, 거래량
        """
        try:
            # 날짜 형식 정규화 (YYYYMMDD)
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")

            logger.info(
                f"OHLCV 조회: stock_code={stock_code}, "
                f"period={start}~{end}, adjust={adjust_price}"
            )

            # pykrx.stock.get_market_ohlcv_by_date
            df = stock.get_market_ohlcv_by_date(
                fromdate=start,
                todate=end,
                ticker=stock_code,
                adjusted=adjust_price  # 수정주가 여부
            )

            if df is None or df.empty:
                logger.warning(f"OHLCV 데이터가 없습니다: {stock_code}")
                return None

            # 컬럼명 영문화 (실제 컬럼 수에 맞춰 동적 처리)
            expected_cols = ["open", "high", "low", "close", "volume"]
            if len(df.columns) >= len(expected_cols):
                df.columns = expected_cols + list(df.columns[len(expected_cols):])
            else:
                logger.warning(f"예상과 다른 컬럼 수: {df.columns}")
                # 기존 컬럼명 유지

            logger.info(f"OHLCV 조회 성공: {len(df)} 일")
            return df

        except Exception as e:
            logger.error(f"OHLCV 조회 실패: {e}", exc_info=True)
            return None

    def get_market_cap(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame | None:
        """
        시가총액 및 거래대금 조회

        Args:
            stock_code: 종목코드
            start_date: 시작일 (YYYYMMDD 또는 YYYY-MM-DD)
            end_date: 종료일 (YYYYMMDD 또는 YYYY-MM-DD)

        Returns:
            시가총액 DataFrame (인덱스: 날짜) 또는 실패 시 None
            컬럼: 종가, 시가총액, 거래량, 거래대금, 상장주식수
        """
        try:
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")

            logger.info(f"시가총액 조회: stock_code={stock_code}, period={start}~{end}")

            # pykrx.stock.get_market_cap_by_date
            df = stock.get_market_cap_by_date(
                fromdate=start,
                todate=end,
                ticker=stock_code
            )

            if df is None or df.empty:
                logger.warning(f"시가총액 데이터가 없습니다: {stock_code}")
                return None

            # 컬럼명 영문화
            # get_market_cap_by_date 반환: 시가총액, 거래량, 거래대금, 상장주식수 (4개)
            # get_market_cap_by_ticker 반환: 종가, 시가총액, 거래량, 거래대금, 상장주식수 (5개)
            if len(df.columns) == 4:
                df.columns = ["market_cap", "volume", "trade_value", "shares_outstanding"]
            elif len(df.columns) == 5:
                df.columns = ["close_price", "market_cap", "volume", "trade_value", "shares_outstanding"]
            else:
                logger.warning(f"예상과 다른 컬럼 수: {df.columns}")

            logger.info(f"시가총액 조회 성공: {len(df)} 일")
            return df

        except Exception as e:
            logger.error(f"시가총액 조회 실패: {e}", exc_info=True)
            return None

    def get_recent_price(self, stock_code: str, days: int = 30) -> pd.DataFrame | None:
        """
        최근 N일간 주가 데이터 조회

        Args:
            stock_code: 종목코드
            days: 조회 일수 (기본값: 30일)

        Returns:
            OHLCV + 시가총액 결합 DataFrame 또는 실패 시 None
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # 휴장일 고려하여 +10일

            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            logger.info(f"최근 {days}일 주가 조회: {stock_code}")

            # OHLCV와 시가총액 동시 조회
            ohlcv_df = self.get_ohlcv(stock_code, start_str, end_str)
            cap_df = self.get_market_cap(stock_code, start_str, end_str)

            if ohlcv_df is None or cap_df is None:
                return None

            # 두 DataFrame 병합
            merged = pd.merge(
                ohlcv_df,
                cap_df[["market_cap", "shares_outstanding"]],
                left_index=True,
                right_index=True,
                how="inner"
            )

            # 최근 N일만 반환
            result = merged.tail(days)

            logger.info(f"최근 주가 조회 성공: {len(result)} 일")
            return result

        except Exception as e:
            logger.error(f"최근 주가 조회 실패: {e}", exc_info=True)
            return None

    def get_fundamentals_range(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame | None:
        """
        날짜 범위의 펀더멘털 지표 (PER, PBR 등) 조회

        Args:
            stock_code: 종목코드
            start_date: 시작일 (YYYYMMDD 또는 YYYY-MM-DD)
            end_date: 종료일 (YYYYMMDD 또는 YYYY-MM-DD)

        Returns:
            펀더멘털 DataFrame (인덱스: 날짜, 컬럼: PER, PBR, EPS, BPS, DIV)
        """
        try:
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")

            logger.info(f"펀더멘털 범위 조회: stock_code={stock_code}, period={start}~{end}")

            df = stock.get_market_fundamental_by_date(
                fromdate=start,
                todate=end,
                ticker=stock_code
            )

            if df is None or df.empty:
                logger.warning(f"펀더멘털 데이터가 없습니다: {stock_code}")
                return None

            logger.info(f"펀더멘털 범위 조회 성공: {len(df)} 일")
            return df

        except Exception as e:
            logger.error(f"펀더멘털 범위 조회 실패: {e}", exc_info=True)
            return None

    def get_fundamental_data(self, stock_code: str, date: str) -> dict[str, Any] | None:
        """
        특정일의 PER, PBR, 배당수익률 등 기본적 분석 지표 조회

        Args:
            stock_code: 종목코드
            date: 조회일 (YYYYMMDD 또는 YYYY-MM-DD)

        Returns:
            기본적 분석 지표 딕셔너리 또는 실패 시 None
        """
        try:
            date_str = date.replace("-", "")

            logger.info(f"펀더멘털 데이터 조회: stock_code={stock_code}, date={date_str}")

            # pykrx.stock.get_market_fundamental_by_date
            df = stock.get_market_fundamental_by_date(
                fromdate=date_str,
                todate=date_str,
                ticker=stock_code
            )

            if df is None or df.empty:
                logger.warning(f"펀더멘털 데이터가 없습니다: {stock_code}")
                return None

            # 가장 최근 날짜의 데이터 추출
            row = df.iloc[-1]

            result = {
                "per": row.get("PER", None),
                "pbr": row.get("PBR", None),
                "dividend_yield": row.get("DIV", None),  # 배당수익률
                "eps": row.get("EPS", None),
                "bps": row.get("BPS", None),
            }

            logger.info("펀더멘털 데이터 조회 성공")
            return result

        except Exception as e:
            logger.error(f"펀더멘털 데이터 조회 실패: {e}", exc_info=True)
            return None

    def get_price_change_rate(self, stock_code: str, days: int = 252) -> dict[str, float] | None:
        """
        수익률 계산 (1개월, 3개월, 6개월, 1년)

        Args:
            stock_code: 종목코드
            days: 조회 기간 (기본값: 252일 = 약 1년)

        Returns:
            기간별 수익률 딕셔너리 또는 실패 시 None
        """
        try:
            df = self.get_recent_price(stock_code, days=days)

            if df is None or len(df) < 20:
                logger.warning(f"수익률 계산을 위한 데이터가 부족합니다: {stock_code}")
                return None

            current_price = df["close"].iloc[-1]

            # 기간별 수익률 계산
            result = {}

            periods = {
                "1m": 20,   # 약 1개월
                "3m": 60,   # 약 3개월
                "6m": 120,  # 약 6개월
                "1y": 252,  # 약 1년
            }

            for period_name, period_days in periods.items():
                if len(df) >= period_days:
                    past_price = df["close"].iloc[-period_days]
                    change_rate = ((current_price - past_price) / past_price) * 100
                    result[period_name] = round(change_rate, 2)

            logger.info(f"수익률 계산 완료: {result}")
            return result

        except Exception as e:
            logger.error(f"수익률 계산 실패: {e}", exc_info=True)
            return None

    def get_52week_high_low(self, stock_code: str) -> dict[str, Any] | None:
        """
        52주 최고가/최저가 조회

        Args:
            stock_code: 종목코드

        Returns:
            52주 최고가/최저가 딕셔너리 또는 실패 시 None
        """
        try:
            df = self.get_recent_price(stock_code, days=252)

            if df is None or df.empty:
                return None

            current_price = df["close"].iloc[-1]
            week_52_high = df["high"].max()
            week_52_low = df["low"].min()

            # 현재가의 52주 최고가/최저가 대비 위치 (%)
            high_ratio = (current_price / week_52_high) * 100
            low_ratio = (current_price / week_52_low) * 100

            result = {
                "current_price": int(current_price),
                "week_52_high": int(week_52_high),
                "week_52_low": int(week_52_low),
                "high_ratio": round(high_ratio, 2),  # 52주 최고가 대비 %
                "low_ratio": round(low_ratio, 2),    # 52주 최저가 대비 %
            }

            logger.info(f"52주 최고가/최저가 조회 완료: {result}")
            return result

        except Exception as e:
            logger.error(f"52주 최고가/최저가 조회 실패: {e}", exc_info=True)
            return None
