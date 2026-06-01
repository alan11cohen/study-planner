from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/study_planner"
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 90

    LLM_PROVIDER: str = "auto"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 30.0

    TASKGEN_MAX_ATTEMPTS: int = 3
    TASKGEN_MIN_TASKS: int = 1
    TASKGEN_MAX_TASKS: int = 20
    TASKGEN_MIN_TASK_HOURS: float = 0.5
    TASKGEN_DEFAULT_HORIZON_WEEKS: int = 8
    TASKGEN_MAX_TASK_HOURS_RATIO: float = 1.5
    TASKGEN_BUDGET_TOLERANCE: float = 1.25

    RAG_PROVIDER: str = "auto"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMS: int = 1536
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.20

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
