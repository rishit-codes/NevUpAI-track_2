from fastapi import APIRouter, Depends, Request
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user_token
from app.models.domain import MemorySession, Trade, Session
from app.schemas.domain import AuditRequest, AuditResponseItem

router = APIRouter()

@router.post("/", response_model=List[AuditResponseItem])
async def audit_sessions(
    request: Request,
    body: AuditRequest,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException
    
    # The prompt doesn't explicitly restrict tenancy here for audit but says "Authenticated."
    # We should ensure the user doing the audit is the same user, or at least that it's authenticated.
    if token_payload.get("sub") != body.userId:
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": "Cross-tenant access denied.", "traceId": request.state.trace_id}
        )
        
    response_items = []
    
    for session_id in body.referencedSessions:
        # Check MemorySession existence
        result = await db.execute(
            select(MemorySession.session_id).where(
                MemorySession.user_id == body.userId,
                MemorySession.session_id == session_id
            )
        )
        found_memory = result.scalar_one_or_none() is not None
        
        # Check Trade/Session table existence as secondary truth
        found_db_session = False
        if not found_memory:
            try:
                import uuid
                s_uuid = uuid.UUID(session_id)
                u_uuid = uuid.UUID(body.userId)
                
                result2 = await db.execute(
                    select(Session.session_id).where(
                        Session.session_id == s_uuid,
                        Session.user_id == u_uuid
                    )
                )
                found_db_session = result2.scalar_one_or_none() is not None
            except ValueError:
                # Invalid UUID format
                pass
                
        response_items.append(AuditResponseItem(
            sessionId=session_id,
            found=found_memory or found_db_session
        ))
        
    return response_items
