from fastapi import Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.plan_service import PlanService
from ..services.task_service import TaskService
from ..services.user_service import UserService


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_plan_service(db: Session = Depends(get_db)) -> PlanService:
    return PlanService(db)


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db)
