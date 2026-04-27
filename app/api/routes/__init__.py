from fastapi import APIRouter
from app.api.routes import memory, audit, sessions
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter()

router.include_router(memory.router, prefix="/memory", tags=["memory"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

class HealthResponse(BaseModel):
    db: str
    queueLag: int
    timestamp: str

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "db": "ok",
        "queueLag": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
