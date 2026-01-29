"""
End-to-End 파이프라인 테스트

전체 LangGraph 파이프라인을 실행하여 기업 분석 보고서를 생성합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import logging

from app.agents.graph import analysis_graph
from app.agents.state import AnalysisState

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_samsung_analysis():
    """삼성전자 전체 파이프라인 테스트"""
    print("\n" + "=" * 80)
    print("E2E 파이프라인 테스트: 삼성전자 (005930)")
    print("=" * 80 + "\n")

    # 초기 상태
    initial_state: AnalysisState = {
        "company_id": 1,
        "stock_code": "005930",
        "company_name": "삼성전자",
        "analysis_run_id": 1,
    }

    print("초기 상태:")
    print(f"  - 기업명: {initial_state['company_name']}")
    print(f"  - 종목코드: {initial_state['stock_code']}")
    print(f"  - Company ID: {initial_state['company_id']}")
    print()

    try:
        print("파이프라인 실행 시작...")
        print("-" * 80)

        # 그래프 실행
        final_state = analysis_graph.invoke(initial_state)

        print("\n" + "=" * 80)
        print("파이프라인 실행 완료!")
        print("=" * 80 + "\n")

        # 결과 출력
        print("최종 상태:")
        print(f"  - 현재 단계: {final_state.get('current_stage')}")
        print(f"  - 에러: {final_state.get('errors', [])}")
        print()

        if final_state.get('deep_value_evaluation'):
            dv_score = final_state['deep_value_evaluation'].get('score', 0)
            print(f"Deep Value 점수: {dv_score}/100")

        if final_state.get('quality_evaluation'):
            q_score = final_state['quality_evaluation'].get('score', 0)
            print(f"Quality 점수: {q_score}/100")

        if final_state.get('overall_score') is not None:
            print(f"종합 점수: {final_state['overall_score']:.1f}/100")

        if final_state.get('overall_verdict'):
            print(f"투자 판단: {final_state['overall_verdict']}")

        if final_state.get('report_id'):
            print(f"\n보고서 ID: {final_state['report_id']}")
            print("보고서가 데이터베이스에 저장되었습니다.")

        # Deep Value 분석 일부 출력
        if final_state.get('deep_value_evaluation'):
            print("\n" + "-" * 80)
            print("Deep Value 분석 (앞부분):")
            print("-" * 80)
            analysis = final_state['deep_value_evaluation'].get('analysis', '')
            print(analysis[:500] + "..." if len(analysis) > 500 else analysis)

        # Quality 분석 일부 출력
        if final_state.get('quality_evaluation'):
            print("\n" + "-" * 80)
            print("Quality 분석 (앞부분):")
            print("-" * 80)
            analysis = final_state['quality_evaluation'].get('analysis', '')
            print(analysis[:500] + "..." if len(analysis) > 500 else analysis)

        return True

    except Exception as e:
        logger.error(f"파이프라인 실행 오류: {e}", exc_info=True)
        print(f"\n❌ 테스트 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("\n" + "=" * 80)
    print("Agent-VI E2E 파이프라인 테스트")
    print("=" * 80)

    success = test_samsung_analysis()

    if success:
        print("\n" + "=" * 80)
        print("✓ 모든 테스트 완료!")
        print("=" * 80 + "\n")
    else:
        print("\n" + "=" * 80)
        print("✗ 테스트 실패")
        print("=" * 80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
