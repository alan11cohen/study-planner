from fastapi import APIRouter, Depends

from ...schemas.study_plan import StudyPlanCreate, StudyPlanRead, StudyPlanUpdate
from ...schemas.study_task import StudyTaskCreate, StudyTaskRead, StudyTaskUpdate
from ...services.plan_service import PlanService
from ...services.task_service import TaskService
from ..deps import get_plan_service, get_task_service

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=StudyPlanRead, status_code=201)
def create_plan(data: StudyPlanCreate, svc: PlanService = Depends(get_plan_service)):
    return svc.create_plan(data)


@router.get("/{plan_id}", response_model=StudyPlanRead)
def get_plan(plan_id: int, svc: PlanService = Depends(get_plan_service)):
    return svc.get_plan(plan_id)


@router.patch("/{plan_id}", response_model=StudyPlanRead)
def update_plan(
    plan_id: int,
    data: StudyPlanUpdate,
    svc: PlanService = Depends(get_plan_service),
):
    return svc.update_plan(plan_id, data)


@router.post("/{plan_id}/tasks", response_model=StudyTaskRead, status_code=201)
def create_task(
    plan_id: int, data: StudyTaskCreate, svc: TaskService = Depends(get_task_service)
):
    return svc.create_task(plan_id, data)


@router.get("/{plan_id}/tasks", response_model=list[StudyTaskRead])
def get_tasks(plan_id: int, svc: TaskService = Depends(get_task_service)):
    return svc.get_tasks_by_plan(plan_id)


@router.patch("/{plan_id}/tasks/{task_id}", response_model=StudyTaskRead)
def update_task(
    plan_id: int,
    task_id: int,
    data: StudyTaskUpdate,
    svc: TaskService = Depends(get_task_service),
):
    return svc.update_task(plan_id, task_id, data)
