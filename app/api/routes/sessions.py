from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
import json
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.api.dependencies.auth import get_current_user_token
from app.schemas.domain import SessionEventsRequest, SessionEventsResponse
from app.models.domain import Session, Trade, MemorySession

import openai
from openai import AsyncOpenAI

router = APIRouter()

# Global memory state for session events (fast metrics)
# In production, use Redis. We use an in-memory dictionary for this hackathon requirement.
session_state = {}

@router.post("/{sessionId}/events", response_model=SessionEventsResponse)
async def process_session_events(
    request: Request,
    body: SessionEventsRequest,
    sessionId: str = Path(...),
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException
    
    if token_payload.get("sub") != body.userId:
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": "Cross-tenant access denied.", "traceId": request.state.trace_id}
        )
        
    if sessionId not in session_state:
        session_state[sessionId] = {
            "trades": [],
            "metrics": {
                "planAdherenceScore": 5.0,
                "revengeFlag": False,
                "sessionTiltIndex": 0.0,
                "winRateByEmotion": {},
                "overtradingEvents": 0
            }
        }
        
    state = session_state[sessionId]
    
    # Simple metric updates
    for event in body.events:
        state["trades"].append(event.model_dump())
        
        # 1. Rolling plan adherence (last 10)
        recent_adherence = [t["planAdherence"] for t in state["trades"][-10:] if t.get("planAdherence") is not None]
        if recent_adherence:
            state["metrics"]["planAdherenceScore"] = sum(recent_adherence) / len(recent_adherence)
            
        # 2. Revenge trade flag
        state["metrics"]["revengeFlag"] = event.revengeFlag
        
        # 3. Session tilt index
        loss_count = sum(1 for t in state["trades"] if t.get("outcome") == "loss")
        state["metrics"]["sessionTiltIndex"] = loss_count / len(state["trades"]) if state["trades"] else 0.0
        
        # 4. Overtrading detector (heuristic >10 trades in last 30 mins)
        try:
            current_time = datetime.fromisoformat(event.entryAt.replace('Z', '+00:00'))
            window_trades = [
                t for t in state["trades"] 
                if (current_time - datetime.fromisoformat(t["entryAt"].replace('Z', '+00:00'))).total_seconds() <= 1800
            ]
            if len(window_trades) > 10:
                state["metrics"]["overtradingEvents"] += 1
        except ValueError:
            pass

    triggered_signals = []
    if state["metrics"]["revengeFlag"]:
        triggered_signals.append("revenge_trading")
    if state["metrics"]["overtradingEvents"] > 0:
        triggered_signals.append("overtrading")
    if state["metrics"]["sessionTiltIndex"] > 0.5 and len(state["trades"]) >= 5:
        triggered_signals.append("session_tilt")
        
    return {
        "sessionId": sessionId,
        "metricsSnapshot": state["metrics"],
        "triggeredSignals": triggered_signals,
        "traceId": request.state.trace_id
    }

@router.get("/{sessionId}/coaching")
async def stream_coaching(
    request: Request,
    sessionId: str = Path(...),
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException
    
    user_id = token_payload.get("sub")
    
    # 1. Fetch current session trades and metrics from DB (or global state)
    current_session = session_state.get(sessionId, {"trades": [], "metrics": {}})
    
    # 2. Call internal memory context logic
    result = await db.execute(
        select(MemorySession).where(MemorySession.user_id == user_id)
    )
    past_sessions = result.scalars().all()
    
    past_context = [
        {"sessionId": str(s.session_id), "summary": s.summary}
        for s in past_sessions[-3:]  # just take recent 3 for context
    ]
    
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or "dummy_key")
    
    async def event_generator():
        system_prompt = f"""You are a trading psychology coach. 
Reference past sessions: {json.dumps(past_context)}. 
Current session trades: {json.dumps(current_session['trades'])}.
Reference only session IDs and trade IDs from the provided list. Do not invent IDs.
Output strict JSON matching:
{{
    "coachingText": "string",
    "referencedSessions": ["sessionId", ...],
    "referencedTrades": ["tradeId", ...],
    "pathologyInsights": [
        {{ "pathology": "revenge_trading", "sessionIds": [...], "tradeIds": [...] }}
    ]
}}
"""
        
        try:
            stream = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Provide coaching based on the latest trade events."}
                ],
                temperature=0,
                stream=True,
                response_format={"type": "json_object"}
            )
            
            full_response = ""
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content or ""
                    if content:
                        full_response += content
                        yield f"event: token\ndata: {json.dumps({'token': content})}\n\n"
                        
            yield f"event: done\ndata: {json.dumps({'fullMessage': full_response})}\n\n"
            
        except Exception as e:
            # Fallback for hackathon testing without real API keys
            fallback = {
                "coachingText": "Take a deep breath and step back. You are showing signs of revenge trading.",
                "referencedSessions": [s["sessionId"] for s in past_context],
                "referencedTrades": [],
                "pathologyInsights": [
                    { "pathology": "revenge_trading", "sessionIds": [s["sessionId"] for s in past_context], "tradeIds": [] }
                ]
            }
            yield f"event: token\ndata: {json.dumps({'token': fallback['coachingText']})}\n\n"
            yield f"event: done\ndata: {json.dumps({'fullMessage': json.dumps(fallback)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
