"""
LLM 프로바이더

LiteLLM을 사용하여 OpenAI, Anthropic 등 여러 LLM 프로바이더를 통합합니다.
"""
import logging
from typing import Any

from litellm import completion, acompletion
from litellm.exceptions import (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """LiteLLM 기반 LLM 프로바이더"""

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        fallback_models: list[str] | None = None
    ):
        """
        Args:
            model: 사용할 LLM 모델 (기본값: settings.DEFAULT_LLM_MODEL)
                - LiteLLM 형식: "gpt-4", "gpt-3.5-turbo", "claude-3-opus", etc.
            temperature: 생성 온도 (0.0~1.0, 기본값: 0.7)
            max_tokens: 최대 생성 토큰 수 (기본값: 4000)
            fallback_models: 폴백 모델 목록 (기본값: None)
        """
        self.model = model or settings.DEFAULT_LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.fallback_models = fallback_models or []

        logger.info(
            f"LLMProvider 초기화: model={self.model}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> str | None:
        """
        동기 completion (LangGraph에서 주로 사용)

        Args:
            messages: 메시지 리스트
                [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."}
                ]
            temperature: 생성 온도 (None이면 기본값 사용)
            max_tokens: 최대 토큰 수 (None이면 기본값 사용)
            **kwargs: 추가 인자 (top_p, stop, etc.)

        Returns:
            생성된 텍스트 또는 실패 시 None
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        # 메인 모델 시도
        result = self._try_completion(
            model=self.model,
            messages=messages,
            temperature=temp,
            max_tokens=max_tok,
            **kwargs
        )

        if result:
            return result

        # 폴백 모델 시도
        for fallback_model in self.fallback_models:
            logger.warning(f"폴백 모델 시도: {fallback_model}")
            result = self._try_completion(
                model=fallback_model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
                **kwargs
            )
            if result:
                return result

        logger.error("모든 모델에서 completion 실패")
        return None

    async def acomplete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> str | None:
        """
        비동기 completion

        Args:
            messages: 메시지 리스트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            **kwargs: 추가 인자

        Returns:
            생성된 텍스트 또는 실패 시 None
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        # 메인 모델 시도
        result = await self._try_acompletion(
            model=self.model,
            messages=messages,
            temperature=temp,
            max_tokens=max_tok,
            **kwargs
        )

        if result:
            return result

        # 폴백 모델 시도
        for fallback_model in self.fallback_models:
            logger.warning(f"폴백 모델 시도: {fallback_model}")
            result = await self._try_acompletion(
                model=fallback_model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
                **kwargs
            )
            if result:
                return result

        logger.error("모든 모델에서 비동기 completion 실패")
        return None

    def _try_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str | None:
        """
        단일 모델로 completion 시도

        Args:
            model: 모델 이름
            messages: 메시지 리스트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            **kwargs: 추가 인자

        Returns:
            생성된 텍스트 또는 실패 시 None
        """
        try:
            logger.debug(f"LLM completion 요청: model={model}, messages={len(messages)}개")

            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            # 응답 파싱
            if response and response.choices:
                content = response.choices[0].message.content

                # 비용 추적 로깅
                usage = getattr(response, "usage", None)
                if usage:
                    logger.info(
                        f"LLM 사용량: model={model}, "
                        f"prompt_tokens={usage.prompt_tokens}, "
                        f"completion_tokens={usage.completion_tokens}, "
                        f"total_tokens={usage.total_tokens}"
                    )

                logger.debug(f"LLM completion 성공: {len(content)} 문자")
                return content

            logger.warning(f"LLM 응답에 content가 없습니다: {response}")
            return None

        except (APIConnectionError, ServiceUnavailableError, Timeout) as e:
            logger.error(f"LLM API 연결 오류 ({model}): {e}")
            return None

        except RateLimitError as e:
            logger.error(f"LLM Rate Limit 초과 ({model}): {e}")
            return None

        except Exception as e:
            logger.error(f"LLM completion 오류 ({model}): {e}", exc_info=True)
            return None

    async def _try_acompletion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str | None:
        """
        단일 모델로 비동기 completion 시도

        Args:
            model: 모델 이름
            messages: 메시지 리스트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            **kwargs: 추가 인자

        Returns:
            생성된 텍스트 또는 실패 시 None
        """
        try:
            logger.debug(f"비동기 LLM completion 요청: model={model}")

            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            if response and response.choices:
                content = response.choices[0].message.content

                # 비용 추적 로깅
                usage = getattr(response, "usage", None)
                if usage:
                    logger.info(
                        f"비동기 LLM 사용량: model={model}, "
                        f"prompt_tokens={usage.prompt_tokens}, "
                        f"completion_tokens={usage.completion_tokens}, "
                        f"total_tokens={usage.total_tokens}"
                    )

                logger.debug(f"비동기 LLM completion 성공: {len(content)} 문자")
                return content

            logger.warning(f"비동기 LLM 응답에 content가 없습니다: {response}")
            return None

        except (APIConnectionError, ServiceUnavailableError, Timeout) as e:
            logger.error(f"비동기 LLM API 연결 오류 ({model}): {e}")
            return None

        except RateLimitError as e:
            logger.error(f"비동기 LLM Rate Limit 초과 ({model}): {e}")
            return None

        except Exception as e:
            logger.error(f"비동기 LLM completion 오류 ({model}): {e}", exc_info=True)
            return None


# 싱글톤 인스턴스
_default_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """
    기본 LLM 프로바이더 싱글톤 가져오기

    Returns:
        LLMProvider 인스턴스
    """
    global _default_provider

    if _default_provider is None:
        # 폴백 체인 설정: Claude 실패 시 GPT로
        fallback_models = []

        if settings.anthropic_api_key and settings.openai_api_key:
            # 둘 다 있으면 Claude 우선, GPT 폴백
            if "claude" in settings.default_llm_model.lower():
                fallback_models = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            else:
                # GPT 우선이면 Claude 폴백
                fallback_models = ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"]

        _default_provider = LLMProvider(
            model=settings.default_llm_model,
            temperature=0.7,
            max_tokens=4000,
            fallback_models=fallback_models
        )

        logger.info(f"기본 LLM 프로바이더 생성: model={settings.default_llm_model}")

    return _default_provider
