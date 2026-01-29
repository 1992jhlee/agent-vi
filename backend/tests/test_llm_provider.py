"""
LLM 프로바이더 테스트

OpenAI API 연동을 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import logging

from app.llm.provider import LLMProvider, get_llm_provider

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_sync_completion():
    """동기 completion 테스트"""
    print("\n" + "=" * 80)
    print("TEST 1: 동기 Completion")
    print("=" * 80)

    provider = get_llm_provider()

    messages = [
        {"role": "system", "content": "당신은 한국 주식시장 전문가입니다."},
        {
            "role": "user",
            "content": "삼성전자(005930)에 대해 50자 이내로 간략히 설명해주세요."
        }
    ]

    response = provider.complete(messages, temperature=0.3, max_tokens=200)

    if response:
        print(f"✓ LLM 응답 성공:\n")
        print(f"{response}\n")
        print(f"응답 길이: {len(response)} 문자")
        return True
    else:
        print(f"✗ LLM 응답 실패")
        return False


async def test_async_completion():
    """비동기 completion 테스트"""
    print("\n" + "=" * 80)
    print("TEST 2: 비동기 Completion")
    print("=" * 80)

    provider = get_llm_provider()

    messages = [
        {"role": "system", "content": "당신은 재무 분석 전문가입니다."},
        {
            "role": "user",
            "content": "PER과 PBR의 차이를 30자 이내로 설명해주세요."
        }
    ]

    response = await provider.acomplete(messages, temperature=0.3, max_tokens=150)

    if response:
        print(f"✓ 비동기 LLM 응답 성공:\n")
        print(f"{response}\n")
        print(f"응답 길이: {len(response)} 문자")
        return True
    else:
        print(f"✗ 비동기 LLM 응답 실패")
        return False


async def test_multiple_requests():
    """여러 요청 병렬 처리 테스트"""
    print("\n" + "=" * 80)
    print("TEST 3: 병렬 요청 처리")
    print("=" * 80)

    provider = get_llm_provider()

    tasks = []

    questions = [
        "KOSPI와 KOSDAQ의 차이는?",
        "배당수익률이란?",
        "ROE는 무엇인가요?",
    ]

    for question in questions:
        messages = [
            {"role": "system", "content": "당신은 주식 투자 교육자입니다."},
            {"role": "user", "content": f"{question} (20자 이내로 답변)"}
        ]
        task = provider.acomplete(messages, temperature=0.3, max_tokens=100)
        tasks.append(task)

    responses = await asyncio.gather(*tasks)

    success_count = sum(1 for r in responses if r is not None)

    print(f"✓ {success_count}/{len(questions)}개 요청 성공\n")

    for idx, (question, response) in enumerate(zip(questions, responses), 1):
        if response:
            print(f"{idx}. Q: {question}")
            print(f"   A: {response}\n")

    return success_count == len(questions)


def test_fallback():
    """폴백 모델 테스트 (일부러 잘못된 모델명 사용)"""
    print("\n" + "=" * 80)
    print("TEST 4: 폴백 체인 테스트")
    print("=" * 80)

    # 잘못된 모델명 + 올바른 폴백 모델
    provider = LLMProvider(
        model="invalid-model-name",
        fallback_models=["gpt-4o", "gpt-3.5-turbo"],
        temperature=0.3,
        max_tokens=150
    )

    messages = [
        {"role": "system", "content": "당신은 도움이 되는 AI입니다."},
        {"role": "user", "content": "안녕하세요 (10자 이내로 답변)"}
    ]

    response = provider.complete(messages)

    if response:
        print(f"✓ 폴백 모델로 응답 성공:")
        print(f"{response}\n")
        return True
    else:
        print(f"✗ 폴백 모델로도 응답 실패")
        return False


def test_temperature_variations():
    """다양한 temperature 테스트"""
    print("\n" + "=" * 80)
    print("TEST 5: Temperature 변화 테스트")
    print("=" * 80)

    provider = get_llm_provider()

    messages = [
        {"role": "system", "content": "당신은 창의적인 작가입니다."},
        {
            "role": "user",
            "content": "투자를 한 단어로 표현한다면? (단어 1개만)"
        }
    ]

    temperatures = [0.0, 0.5, 1.0]

    print("동일한 질문에 다른 temperature로 답변:\n")

    for temp in temperatures:
        response = provider.complete(messages, temperature=temp, max_tokens=50)

        if response:
            print(f"Temperature {temp}: {response}")
        else:
            print(f"Temperature {temp}: (응답 실패)")

    return True


async def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 80)
    print("LLM 프로바이더 통합 테스트")
    print("=" * 80)

    # TEST 1: 동기 completion
    test_sync_completion()

    # TEST 2: 비동기 completion
    await test_async_completion()

    # TEST 3: 병렬 요청
    await test_multiple_requests()

    # TEST 4: 폴백 체인
    test_fallback()

    # TEST 5: Temperature
    test_temperature_variations()

    print("\n" + "=" * 80)
    print("✓ 모든 테스트 완료")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)
        print(f"\n❌ 테스트 실패: {e}")
