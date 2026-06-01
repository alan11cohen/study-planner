from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMClient(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    def parse(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        temperature: float = 0.2,
        context: dict | None = None,
    ) -> T: ...
