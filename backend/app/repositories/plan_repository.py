from sqlalchemy.orm import Session

from ..models.study_plan import StudyPlan
from ..schemas.study_plan import StudyPlanCreate, StudyPlanUpdate


class PlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: StudyPlanCreate) -> StudyPlan:
        plan = StudyPlan(**data.model_dump())
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_by_id(self, plan_id: int) -> StudyPlan | None:
        return self.db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()

    def get_by_user_id(self, user_id: int) -> list[StudyPlan]:
        return self.db.query(StudyPlan).filter(StudyPlan.user_id == user_id).all()

    def update(self, plan_id: int, data: StudyPlanUpdate) -> StudyPlan | None:
        plan = self.get_by_id(plan_id)
        if not plan:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(plan, field, value)
        self.db.commit()
        self.db.refresh(plan)
        return plan
