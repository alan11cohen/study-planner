from fastapi import APIRouter, Depends, File, UploadFile

from ...schemas.document import ChatRequest, ChatResponse, PlanDocumentRead
from ...services.chat_service import ChatService
from ...services.document_service import DocumentService
from ..deps import get_chat_service, get_document_service

router = APIRouter(prefix="/plans", tags=["documents"])


@router.post("/{plan_id}/documents", response_model=PlanDocumentRead, status_code=201)
async def upload_document(
    plan_id: int,
    file: UploadFile = File(...),
    svc: DocumentService = Depends(get_document_service),
):
    content = await file.read()
    return svc.upload(
        plan_id=plan_id,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )


@router.get("/{plan_id}/documents", response_model=list[PlanDocumentRead])
def list_documents(
    plan_id: int,
    svc: DocumentService = Depends(get_document_service),
):
    return svc.list_documents(plan_id)


@router.post("/{plan_id}/documents/chat", response_model=ChatResponse)
def chat(
    plan_id: int,
    req: ChatRequest,
    svc: ChatService = Depends(get_chat_service),
):
    return svc.chat(plan_id, req.question)
