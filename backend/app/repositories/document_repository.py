from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.plan_document import PlanDocument


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        plan_id: int,
        filename: str,
        content_type: str,
        size_bytes: int,
        chunk_count: int = 0,
    ) -> PlanDocument:
        doc = PlanDocument(
            plan_id=plan_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            chunk_count=chunk_count,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update_chunk_count(self, doc_id: int, chunk_count: int) -> None:
        self.db.query(PlanDocument).filter(PlanDocument.id == doc_id).update(
            {"chunk_count": chunk_count}
        )
        self.db.commit()

    def delete(self, doc_id: int) -> None:
        self.db.query(PlanDocument).filter(PlanDocument.id == doc_id).delete()
        self.db.commit()

    def get_by_plan_id(self, plan_id: int) -> list[PlanDocument]:
        return (
            self.db.query(PlanDocument)
            .filter(PlanDocument.plan_id == plan_id)
            .order_by(PlanDocument.created_at)
            .all()
        )
