from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..ai.rag.base import Ingester, RAGError
from ..repositories.document_repository import DocumentRepository
from ..repositories.plan_repository import PlanRepository
from ..schemas.document import PlanDocumentRead

_ALLOWED_TYPES = {"application/pdf"}
_MAX_SIZE_BYTES = 20 * 1024 * 1024


class DocumentService:
    def __init__(self, db: Session, ingester: Ingester) -> None:
        self._plan_repo = PlanRepository(db)
        self._doc_repo = DocumentRepository(db)
        self._ingester = ingester

    def upload(
        self,
        plan_id: int,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> PlanDocumentRead:
        plan = self._plan_repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        if content_type not in _ALLOWED_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type '{content_type}'. Only PDF files are accepted.",
            )
        if len(content) > _MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum allowed size is {_MAX_SIZE_BYTES // (1024*1024)} MB.",
            )

        doc = self._doc_repo.create(
            plan_id=plan_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
        )

        try:
            chunk_count = self._ingester.ingest(
                content=content,
                filename=filename,
                plan_id=plan_id,
                document_id=doc.id,
            )
        except RAGError as exc:
            self._doc_repo.delete(doc.id)
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        self._doc_repo.update_chunk_count(doc.id, chunk_count)
        doc.chunk_count = chunk_count
        return PlanDocumentRead.model_validate(doc)

    def list_documents(self, plan_id: int) -> list[PlanDocumentRead]:
        plan = self._plan_repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        docs = self._doc_repo.get_by_plan_id(plan_id)
        return [PlanDocumentRead.model_validate(d) for d in docs]
