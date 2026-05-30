from fastapi import APIRouter, Depends

from ...schemas.study_plan import StudyPlanRead
from ...schemas.user import UserCreate, UserRead
from ...services.plan_service import PlanService
from ...services.user_service import UserService
from ..deps import get_plan_service, get_user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(svc: UserService = Depends(get_user_service)):
    return svc.get_all_users()


@router.post("", response_model=UserRead, status_code=201)
def create_user(data: UserCreate, svc: UserService = Depends(get_user_service)):
    return svc.create_user(data)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, svc: UserService = Depends(get_user_service)):
    return svc.get_user(user_id)


@router.get("/{user_id}/plans", response_model=list[StudyPlanRead])
def get_user_plans(user_id: int, svc: PlanService = Depends(get_plan_service)):
    return svc.get_plans_by_user(user_id)
