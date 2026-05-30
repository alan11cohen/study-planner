from sqlalchemy.orm import Session

from ..models.study_task import StudyTask
from ..schemas.study_task import StudyTaskCreate, StudyTaskUpdate


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, plan_id: int, data: StudyTaskCreate) -> StudyTask:
        task = StudyTask(plan_id=plan_id, **data.model_dump())
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: int) -> StudyTask | None:
        return self.db.query(StudyTask).filter(StudyTask.id == task_id).first()

    def get_by_plan_id(self, plan_id: int) -> list[StudyTask]:
        return self.db.query(StudyTask).filter(StudyTask.plan_id == plan_id).all()

    def update(self, task_id: int, data: StudyTaskUpdate) -> StudyTask | None:
        task = self.get_by_id(task_id)
        if not task:
            return None
        for field, value in data.model_dump().items():
            setattr(task, field, value)
        self.db.commit()
        self.db.refresh(task)
        return task
