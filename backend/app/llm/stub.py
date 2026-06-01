from __future__ import annotations

from typing import Callable, TypeVar

from pydantic import BaseModel

from .base import LLMClient, LLMError

T = TypeVar("T", bound=BaseModel)

Fabricator = Callable[[dict], dict]
_FABRICATORS: dict[str, Fabricator] = {}


def register_fabricator(schema: type[BaseModel], fabricator: Fabricator) -> None:
    _FABRICATORS[schema.__name__] = fabricator


class StubLLMClient(LLMClient):
    @property
    def model_name(self) -> str:
        return "stub-offline"

    def parse(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        temperature: float = 0.2,
        context: dict | None = None,
    ) -> T:
        fabricator = _FABRICATORS.get(schema.__name__)
        if fabricator is None:
            raise LLMError(
                f"No offline fabricator registered for '{schema.__name__}'. "
                "Configure a real LLM provider (set OPENAI_API_KEY) or register "
                "a stub fabricator for this schema."
            )
        payload = fabricator(context or {})
        return schema.model_validate(payload)
