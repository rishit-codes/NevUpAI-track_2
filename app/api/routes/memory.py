from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
import uuid

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user_token
from app.models.domain import MemorySession
from app.schemas.domain import MemorySessionUpsertRequest, MemorySessionResponse, ContextSessionsResponse

router = APIRouter()

@router.put("/{userId}/sessions/{sessionId}", response_model=MemorySessionResponse)
async def upsert_memory_session(
    request: Request,
    body: MemorySessionUpsertRequest,
    userId: str = Path(...),
    sessionId: str = Path(...),
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException
    
    # Enforce tenancy explicitly, as well as via dependency
    if token_payload.get("sub") != userId:
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": "Cross-tenant access denied.", "traceId": request.state.trace_id}
        )

    u_uuid = uuid.UUID(userId)
    s_uuid = uuid.UUID(sessionId)

    stmt = insert(MemorySession).values(
        user_id=u_uuid,
        session_id=s_uuid,
        summary=body.summary,
        metrics_json=body.metrics,
        tags=body.tags
    )
    
    stmt = stmt.on_conflict_do_update(
        index_elements=['user_id', 'session_id'],
        set_={
            'summary': stmt.excluded.summary,
            'metrics_json': stmt.excluded.metrics_json,
            'tags': stmt.excluded.tags
        }
    ).returning(MemorySession)
    
    result = await db.execute(stmt)
    await db.commit()
    
    db_obj = result.scalar_one()
    
    return {
        "userId": str(db_obj.user_id),
        "sessionId": str(db_obj.session_id),
        "summary": db_obj.summary,
        "metrics": db_obj.metrics_json,
        "tags": db_obj.tags,
        "createdAt": db_obj.created_at,
        "updatedAt": db_obj.updated_at
    }

@router.get("/{userId}/sessions/{sessionId}", response_model=MemorySessionResponse)
async def get_memory_session(
    request: Request,
    userId: str = Path(...),
    sessionId: str = Path(...),
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException
    
    if token_payload.get("sub") != userId:
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": "Cross-tenant access denied.", "traceId": request.state.trace_id}
        )
        
    u_uuid = uuid.UUID(userId)
    s_uuid = uuid.UUID(sessionId)
        
    result = await db.execute(
        select(MemorySession).where(
            MemorySession.user_id == u_uuid,
            MemorySession.session_id == s_uuid
        )
    )
    db_obj = result.scalar_one_or_none()
    
    if not db_obj:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Session not found", "traceId": request.state.trace_id}
        )
        
    return {
        "userId": str(db_obj.user_id),
        "sessionId": str(db_obj.session_id),
        "summary": db_obj.summary,
        "metrics": db_obj.metrics_json,
        "tags": db_obj.tags,
        "createdAt": db_obj.created_at,
        "updatedAt": db_obj.updated_at
    }

@router.get("/{userId}/context", response_model=ContextSessionsResponse)
async def get_memory_context(
    request: Request,
    userId: str = Path(...),
    relevantTo: str = Query(...),
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException
    
    if token_payload.get("sub") != userId:
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": "Cross-tenant access denied.", "traceId": request.state.trace_id}
        )
        
    u_uuid = uuid.UUID(userId)
        
    # Naive filtering for relevant tags using LIKE
    # Assuming tags array, we can use ANY operator in postgres or filter python-side
    result = await db.execute(
        select(MemorySession).where(MemorySession.user_id == u_uuid)
    )
    
    db_objs = result.scalars().all()
    
    sessions = []
    pattern_ids = []
    
    for obj in db_objs:
        # Partial match
        is_relevant = any(relevantTo.lower() in t.lower() for t in obj.tags)
        if is_relevant:
            sessions.append({
                "sessionId": str(obj.session_id),
                "summary": obj.summary,
                "tags": obj.tags
            })
            
    # For patternIds, just add relevantTo string
    if sessions:
        pattern_ids.append(relevantTo)
            
    return {
        "sessions": sessions,
        "patternIds": pattern_ids
    }
