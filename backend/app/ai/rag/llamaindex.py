from __future__ import annotations

import io
from urllib.parse import urlparse

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores.types import (
    MetadataFilter,
    MetadataFilters,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from pypdf import PdfReader

from ...core.config import settings
from .base import Ingester, RAGError, Retriever, RetrievedChunk

_TABLE_NAME = "document_chunks"


def _build_vector_store() -> PGVectorStore:
    parsed = urlparse(settings.DATABASE_URL)
    return PGVectorStore.from_params(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password or "",
        table_name=_TABLE_NAME,
        embed_dim=settings.EMBEDDING_DIMS,
    )


def _build_embed_model() -> OpenAIEmbedding:
    return OpenAIEmbedding(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
        dimensions=settings.EMBEDDING_DIMS,
    )


def _parse_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())


class LlamaIndexIngester(Ingester):
    def __init__(self) -> None:
        self._vector_store = _build_vector_store()
        self._embed_model = _build_embed_model()
        self._splitter = SentenceSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )

    def ingest(
        self,
        content: bytes,
        filename: str,
        plan_id: int,
        document_id: int,
    ) -> int:
        try:
            text = _parse_pdf(content)
            if not text:
                raise RAGError(f"Could not extract text from '{filename}'.")

            doc = Document(
                text=text,
                metadata={
                    "plan_id": str(plan_id),
                    "document_id": str(document_id),
                    "filename": filename,
                },
            )

            nodes = self._splitter.get_nodes_from_documents([doc])
            for i, node in enumerate(nodes):
                node.metadata["chunk_index"] = str(i)

            pipeline = IngestionPipeline(
                transformations=[self._embed_model],
                vector_store=self._vector_store,
            )
            pipeline.run(nodes=nodes)
            return len(nodes)
        except RAGError:
            raise
        except Exception as exc:
            raise RAGError(f"Ingestion failed for '{filename}': {exc}") from exc


class LlamaIndexRetriever(Retriever):
    def __init__(self) -> None:
        self._vector_store = _build_vector_store()
        self._embed_model = _build_embed_model()

    def retrieve(self, query: str, plan_id: int) -> list[RetrievedChunk]:
        try:
            storage_context = StorageContext.from_defaults(
                vector_store=self._vector_store
            )
            index = VectorStoreIndex.from_vector_store(
                self._vector_store,
                embed_model=self._embed_model,
                storage_context=storage_context,
            )
            filters = MetadataFilters(
                filters=[MetadataFilter(key="plan_id", value=str(plan_id))]
            )
            retriever = index.as_retriever(
                similarity_top_k=settings.RAG_TOP_K,
                filters=filters,
            )
            nodes = retriever.retrieve(query)

            threshold = settings.RAG_SCORE_THRESHOLD
            chunks = [
                RetrievedChunk(
                    text=node.get_content(),
                    filename=node.metadata.get("filename", "unknown"),
                    score=node.score or 0.0,
                    chunk_index=int(node.metadata.get("chunk_index", 0)),
                    document_id=int(node.metadata.get("document_id", 0)),
                )
                for node in nodes
                if (node.score or 0.0) >= threshold
            ]

            return sorted(chunks, key=lambda c: (c.document_id, c.chunk_index))
        except Exception as exc:
            raise RAGError(f"Retrieval failed: {exc}") from exc
