from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.system_user import SystemUser
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services import assistant_service
from app.services.llm_service import GeminiUnavailableError

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def chat(
    payload: AssistantChatRequest, db: Session = Depends(get_db),
    _: SystemUser = Depends(get_current_user),
):
    try:
        reply = assistant_service.ask(
            db, payload.message, [h.model_dump() for h in payload.history]
        )
    except GeminiUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return AssistantChatResponse(reply=reply)
