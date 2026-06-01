from fastapi import Depends
from sqlalchemy.orm import Session

from ..ai.task_generation import TaskGenerator
from ..core.database import get_db
from ..llm import get_llm_client
from ..services.plan_service import PlanService
from ..services.task_generation_service import TaskGenerationService
from ..services.task_service import TaskService
from ..services.user_service import UserService


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_plan_service(db: Session = Depends(get_db)) -> PlanService:
    return PlanService(db)


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db)


def get_task_generation_service(
    db: Session = Depends(get_db),
) -> TaskGenerationService:
    generator = TaskGenerator(get_llm_client())
    return TaskGenerationService(db, generator)
