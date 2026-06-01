from __future__ import annotations

from typing import TypeVar

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from .base import LLMClient, LLMError

T = TypeVar("T", bound=BaseModel)


class OpenAIClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def parse(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        temperature: float = 0.2,
        context: dict | None = None,
    ) -> T:
        try:
            completion = self._client.beta.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format=schema,
                temperature=temperature,
            )
        except OpenAIError as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc

        choice = completion.choices[0]
        message = choice.message

        if getattr(message, "refusal", None):
            raise LLMError(f"Model refused the request: {message.refusal}")
        if choice.finish_reason == "length":
            raise LLMError("Model output was truncated before completing the schema")
        if message.parsed is None:
            try:
                return schema.model_validate_json(message.content or "")
            except ValidationError as exc:
                raise LLMError(f"Could not parse model output: {exc}") from exc

        return message.parsed
