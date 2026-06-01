from __future__ import annotations

from functools import lru_cache

from ..core.config import settings
from .base import LLMClient, LLMError
from .stub import StubLLMClient


def _build_client() -> LLMClient:
    provider = settings.LLM_PROVIDER.lower()
    has_key = bool(settings.OPENAI_API_KEY)

    if provider == "stub":
        return StubLLMClient()

    if provider == "openai" or (provider == "auto" and has_key):
        if not has_key:
            raise LLMError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "Set the key or use LLM_PROVIDER=stub for offline mode."
            )
        from .openai_client import OpenAIClient

        return OpenAIClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

    if provider == "auto":
        return StubLLMClient()

    raise LLMError(f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'")


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return _build_client()
