from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..ai.rag import rag_fabricator  # noqa: F401
from ..ai.rag.base import RAGError, Retriever
from ..ai.rag.prompts import RAG_SYSTEM_PROMPT, build_rag_user_prompt
from ..ai.rag.schemas import RAGAnswer
from ..llm.base import LLMClient, LLMError
from ..repositories.plan_repository import PlanRepository
from ..schemas.document import ChatResponse


class ChatService:
    def __init__(self, db: Session, retriever: Retriever, llm: LLMClient) -> None:
        self._plan_repo = PlanRepository(db)
        self._retriever = retriever
        self._llm = llm

    def chat(self, plan_id: int, question: str) -> ChatResponse:
        plan = self._plan_repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        try:
            chunks = self._retriever.retrieve(question, plan_id)
        except RAGError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        user_prompt = build_rag_user_prompt(question, chunks)

        try:
            result: RAGAnswer = self._llm.parse(
                system=RAG_SYSTEM_PROMPT,
                user=user_prompt,
                schema=RAGAnswer,
                context={"chunks": [c.text for c in chunks]},
            )
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc

        return ChatResponse(
            answer=result.answer,
            sources=list({chunk.filename for chunk in chunks}),
            grounded=result.has_relevant_context,
        )
