from pydantic import BaseModel, Field


class RAGAnswer(BaseModel):
    answer: str = Field(description="Answer grounded in the provided context.")
    has_relevant_context: bool = Field(
        description=(
            "True if the context excerpts contained information relevant to the question. "
            "False if no relevant information was found."
        )
    )
