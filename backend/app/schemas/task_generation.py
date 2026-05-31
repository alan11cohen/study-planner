from pydantic import BaseModel, Field

from .study_task import StudyTaskRead


class GenerateTasksRequest(BaseModel):

    count: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Desired number of tasks. Omit to let the planner decide.",
    )
    extra_instructions: str | None = Field(
        default=None,
        max_length=500,
        description="Free-form guidance to steer generation (e.g. 'focus on hands-on labs').",
    )
    replace_existing: bool = Field(
        default=False,
        description="If true, existing tasks for the plan are deleted before inserting.",
    )


class GenerateTasksResponse(BaseModel):
    plan_id: int
    tasks: list[StudyTaskRead]
    model: str
    attempts: int
    warnings: list[str] = []
