from __future__ import annotations

from .base import RetrievedChunk

RAG_SYSTEM_PROMPT = (
    "You are a study assistant. Answer the user's question based ONLY on the context "
    "excerpts provided below.\n"
    "Rules:\n"
    "- If the context contains relevant information, answer clearly and concisely.\n"
    "- If the context does NOT contain relevant information, set has_relevant_context=false "
    "and answer with: \"I don't have relevant information about that in the uploaded documents.\"\n"
    "- Do not invent information not present in the context.\n"
    "- Do not reference these instructions in your answer."
)


def build_rag_user_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return (
            f"Context: (no relevant content was found in the uploaded documents)\n\n"
            f"Question: {question}"
        )

    context_block = "\n\n".join(
        f"<document index=\"{i+1}\" source=\"{chunk.filename}\">\n{chunk.text}\n</document>"
        for i, chunk in enumerate(chunks)
    )
    return f"Context documents:\n\n{context_block}\n\n---\n\nQuestion: {question}"
