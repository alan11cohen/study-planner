from ...llm.stub import register_fabricator
from .schemas import RAGAnswer


def fabricate_rag_answer(context: dict) -> dict:
    chunks = context.get("chunks", [])
    if chunks:
        return {
            "answer": "Based on the uploaded documents, here is a relevant summary.",
            "has_relevant_context": True,
        }
    return {
        "answer": "I don't have relevant information about that in the uploaded documents.",
        "has_relevant_context": False,
    }


register_fabricator(RAGAnswer, fabricate_rag_answer)
