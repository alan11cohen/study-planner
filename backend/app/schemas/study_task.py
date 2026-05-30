from pydantic import BaseModel


class StudyTaskCreate(BaseModel):
    title: str
    estimated_hours: float


class StudyTaskUpdate(BaseModel):
    completed: bool


class StudyTaskRead(BaseModel):
    id: int
    plan_id: int
    title: str
    estimated_hours: float
    completed: bool

    model_config = {"from_attributes": True}
