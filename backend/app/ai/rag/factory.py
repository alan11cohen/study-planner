from __future__ import annotations

from functools import lru_cache

from ...core.config import settings
from .base import Ingester, Retriever


def _use_stub() -> bool:
    if settings.RAG_PROVIDER == "stub":
        return True
    if settings.RAG_PROVIDER == "auto" and not settings.OPENAI_API_KEY:
        return True
    return False


@lru_cache(maxsize=1)
def _build_ingester() -> Ingester:
    if _use_stub():
        from .stub import StubIngester
        return StubIngester()
    from .llamaindex import LlamaIndexIngester
    return LlamaIndexIngester()


@lru_cache(maxsize=1)
def _build_retriever() -> Retriever:
    if _use_stub():
        from .stub import StubRetriever
        return StubRetriever()
    from .llamaindex import LlamaIndexRetriever
    return LlamaIndexRetriever()


def get_ingester() -> Ingester:
    return _build_ingester()


def get_retriever() -> Retriever:
    return _build_retriever()
