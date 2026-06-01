from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from ...schemas.agent import AgentGenerateRequest, AgentGenerateResponse
from ...services.agent_service import AgentService
from ..deps import get_agent_service

router = APIRouter(prefix="/plans", tags=["agent"])


@router.post(
    "/{plan_id}/agent-generate-tasks",
    response_model=AgentGenerateResponse,
    status_code=201,
)
def agent_generate_tasks(
    plan_id: int,
    req: AgentGenerateRequest = Body(default_factory=AgentGenerateRequest),
    svc: AgentService = Depends(get_agent_service),
) -> AgentGenerateResponse:
    return svc.run(plan_id, req)
