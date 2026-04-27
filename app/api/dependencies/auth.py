from fastapi import Depends, HTTPException, Request, Header
from app.core.security import decode_token
from typing import Optional

async def get_current_user_token(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> dict:
    trace_id = getattr(request.state, "trace_id", "unknown")
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "message": "Missing or invalid Authorization header", "traceId": trace_id}
        )
    
    token = authorization.split(" ")[1]
    try:
        payload = decode_token(token)
        # Store user_id in request state for logging
        request.state.user_id = payload.get("sub")
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "message": str(e), "traceId": trace_id}
        )

def require_user_tenancy(user_id: str):
    async def enforce_tenancy(
        request: Request,
        token_payload: dict = Depends(get_current_user_token)
    ):
        trace_id = getattr(request.state, "trace_id", "unknown")
        token_user_id = token_payload.get("sub")
        
        if token_user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail={"error": "FORBIDDEN", "message": "Cross-tenant access denied.", "traceId": trace_id}
            )
        return token_payload
    return enforce_tenancy
