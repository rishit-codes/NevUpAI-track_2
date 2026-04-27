from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class BehavioralMetrics(BaseModel):
    planAdherenceScore: Optional[float] = None
    revengeFlag: Optional[bool] = None
    sessionTiltIndex: Optional[float] = None
    winRateByEmotion: Optional[Dict[str, float]] = None
    overtradingEvents: Optional[int] = None
    
    class Config:
        extra = "allow"

class MemorySessionUpsertRequest(BaseModel):
    summary: str
    metrics: Dict[str, Any]
    tags: List[str]

class MemorySessionResponse(BaseModel):
    userId: str
    sessionId: str
    summary: str
    metrics: Dict[str, Any]
    tags: List[str]
    createdAt: datetime
    updatedAt: datetime

class ContextSessionsResponse(BaseModel):
    sessions: List[Dict[str, Any]]
    patternIds: List[str]

class TradeEvent(BaseModel):
    tradeId: str
    asset: str
    assetClass: str
    direction: str
    entryPrice: float
    quantity: float
    entryAt: str
    exitPrice: Optional[float] = None
    exitAt: Optional[str] = None
    status: str
    outcome: Optional[str] = None
    pnl: Optional[float] = None
    planAdherence: Optional[int] = None
    emotionalState: Optional[str] = None
    entryRationale: Optional[str] = None
    revengeFlag: Optional[bool] = False

class SessionEventsRequest(BaseModel):
    userId: str
    events: List[TradeEvent]

class SessionEventsResponse(BaseModel):
    sessionId: str
    metricsSnapshot: Dict[str, Any]
    triggeredSignals: List[str]
    traceId: str

class AuditRequest(BaseModel):
    userId: str
    referencedSessions: List[str]

class AuditResponseItem(BaseModel):
    sessionId: str
    found: bool
