from __future__ import annotations

from .base import Ingester, Retriever, RetrievedChunk

_store: dict[int, list[RetrievedChunk]] = {}


class StubIngester(Ingester):
    def ingest(
        self,
        content: bytes,
        filename: str,
        plan_id: int,
        document_id: int,
    ) -> int:
        chunk = RetrievedChunk(
            text=f"[stub content of {filename}]",
            filename=filename,
            score=1.0,
        )
        _store.setdefault(plan_id, []).append(chunk)
        return 1


class StubRetriever(Retriever):
    def retrieve(self, query: str, plan_id: int) -> list[RetrievedChunk]:
        return list(_store.get(plan_id, []))


def clear_stub_store() -> None:
    _store.clear()
