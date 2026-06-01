from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class RAGError(Exception):
    pass


@dataclass
class RetrievedChunk:
    text: str
    filename: str
    score: float
    chunk_index: int = 0
    document_id: int = 0


class Ingester(ABC):
    @abstractmethod
    def ingest(
        self,
        content: bytes,
        filename: str,
        plan_id: int,
        document_id: int,
    ) -> int: ...


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, plan_id: int) -> list[RetrievedChunk]: ...
