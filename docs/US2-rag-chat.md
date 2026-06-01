# US2 — Document-Grounded Chat (RAG): Technical Decisions

## What it does

Two endpoints implement document-grounded study chat:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/plans/{id}/documents` | Upload a PDF, ingest it into the vector store, and record it in the database |
| `GET` | `/plans/{id}/documents` | List uploaded documents for a plan |
| `POST` | `/plans/{id}/documents/chat` | Ask a natural-language question answered from uploaded material only |

The upload pipeline extracts text from the PDF, chunks it, embeds the chunks, and persists them in pgvector. The chat pipeline embeds the question, retrieves the most relevant chunks, and asks the LLM to answer strictly from that context.

---

## RAG framework: custom vs LlamaIndex

### Option A — Fully custom pipeline

Implement PDF parsing, chunking, embedding calls, and pgvector queries directly using `psycopg2` and the OpenAI embeddings API.

**Discarded because:**
- Standard RAG infrastructure (chunking strategy, embedding batching, metadata filtering, vector retrieval) is non-trivial to implement correctly and test in isolation.
- The main risk is not the LLM call but the retrieval quality — chunking parameters, similarity metrics, and metadata handling all affect output. LlamaIndex has established defaults that encode this knowledge.
- A custom implementation would duplicate effort that LlamaIndex already provides with a transparent and auditable pipeline.

### Option B — LlamaIndex (chosen)

LlamaIndex provides `SentenceSplitter`, `IngestionPipeline`, `PGVectorStore`, and `VectorStoreIndex` as composable primitives. Each stage is explicit and replaceable.

**Chosen because:**
- The ingestion and retrieval pipeline is transparent: every transformation (chunking → embedding → storage) is a named step.
- `PGVectorStore` integrates directly with the existing PostgreSQL instance (pgvector extension). No additional infrastructure.
- Retrieval parameters (chunk size, overlap, top-k, score threshold) are configurable without touching the LlamaIndex internals.
- Production-readiness: LlamaIndex is a widely adopted RAG framework. 

---

## Ingestion pipeline

```
PDF bytes
  └─► pypdf.PdfReader        — text extraction per page
        └─► SentenceSplitter  — sentence-aware chunking (chunk_size, chunk_overlap)
              └─► chunk metadata: plan_id, document_id, filename, chunk_index
                    └─► OpenAIEmbedding (text-embedding-3-small)
                          └─► PGVectorStore (pgvector table: document_chunks)
```

`chunk_index` records the position of each chunk within its source document. `document_id` records which document a chunk belongs to. Both are used during retrieval to restore narrative ordering.

---

## Retrieval pipeline

```
question string
  └─► embed question (text-embedding-3-small)
        └─► pgvector similarity search (top_k=RAG_TOP_K, filtered by plan_id)
              └─► filter chunks below RAG_SCORE_THRESHOLD
                    └─► sort by (document_id, chunk_index)  ← restore reading order
                          └─► build prompt with <document> tags
                                └─► LLM answers strictly from context
```

---

## Key design decisions

### Per-plan isolation

All chunks stored in pgvector carry a `plan_id` metadata field. Every retrieval applies a `MetadataFilter(key="plan_id", value=str(plan_id))` before searching. Documents from one plan cannot surface in queries from another plan, regardless of semantic similarity.

### Narrative ordering

Vector similarity optimises for relevance, not reading order. Retrieved chunks are reordered by `(document_id, chunk_index)` before reaching the LLM. This ensures that multi-chunk context reads coherently — especially important for structured material like textbooks or lecture notes where concepts build on each other.

### Similarity thresholding

Chunks with a similarity score below `RAG_SCORE_THRESHOLD` (default `0.20`) are discarded. This prevents the LLM from receiving weakly-related content and generating plausible-sounding but ungrounded answers. `RAG_TOP_K` is intentionally set slightly above the desired context size so that thresholding does not starve the model when some chunks pass the threshold and others do not.

The threshold of `0.20` was determined empirically: real queries against uploaded PDF and lecture material produced scores in the `0.23–0.36` range. A threshold of `0.40` was too restrictive; `0.20` passes relevant content while rejecting noise.

### Explicit grounding signal

The LLM is instructed via `has_relevant_context` (a boolean field in the structured output schema `RAGAnswer`) to declare whether the retrieved context contains relevant information. When `has_relevant_context=false`, the response surfaces "no relevant content was found" rather than an invented answer. This is an explicit, machine-readable signal — not an inference from the answer text.

### Prompt injection mitigation

Retrieved chunks are wrapped in `<document index="N" source="filename">` XML tags. This separates user-provided content from system instructions, reducing the risk of a malicious document injecting instructions into the LLM prompt.

### Offline-first testing

`Ingester` and `Retriever` are abstract base classes. `StubIngester` and `StubRetriever` provide deterministic in-memory implementations. The factory (`rag/factory.py`) selects the stub automatically when `RAG_PROVIDER=auto` and no `OPENAI_API_KEY` is set, so the full test suite runs without pgvector or OpenAI credentials.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `RAG_PROVIDER` | `auto` | `auto` selects `llamaindex` when `OPENAI_API_KEY` is set, `stub` otherwise. |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model used for ingestion and retrieval. Must match between both operations. |
| `EMBEDDING_DIMS` | `1536` | Embedding vector dimensions. Must match the pgvector column definition. |
| `RAG_CHUNK_SIZE` | `512` | Maximum tokens per chunk. Controls context granularity. |
| `RAG_CHUNK_OVERLAP` | `50` | Token overlap between consecutive chunks. Prevents context loss at chunk boundaries. |
| `RAG_TOP_K` | `5` | Number of chunks retrieved before score thresholding. |
| `RAG_SCORE_THRESHOLD` | `0.20` | Minimum cosine similarity score for a chunk to be included in the prompt. |
