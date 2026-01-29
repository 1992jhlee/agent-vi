"""LLM provider configuration using LiteLLM for multi-provider support."""

from litellm import completion

from app.config import settings


def get_llm_response(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Get a response from the configured LLM provider.

    Uses LiteLLM to support multiple providers (OpenAI, Anthropic, etc.)
    with a unified interface.
    """
    model = model or settings.default_llm_model

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


async def get_llm_response_async(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Async version of get_llm_response."""
    from litellm import acompletion

    model = model or settings.default_llm_model

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = await acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content
