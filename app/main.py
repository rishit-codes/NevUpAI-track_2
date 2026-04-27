from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uuid
import time
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="NevUp AI Trading Coach", version="1.0.0")

from app.api.routes import router as api_router
app.include_router(api_router)


@app.middleware("http")
async def add_trace_id_and_log(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        latency_ms = int((time.time() - start_time) * 1000)
        
        # User ID extraction from request state if authenticated
        user_id = getattr(request.state, "user_id", None)
        
        log_entry = {
            "traceId": trace_id,
            "userId": user_id,
            "path": request.url.path,
            "method": request.method,
            "statusCode": response.status_code,
            "latencyMs": latency_ms
        }
        logger.info(log_entry)
        
        return response
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        user_id = getattr(request.state, "user_id", None)
        
        log_entry = {
            "traceId": trace_id,
            "userId": user_id,
            "path": request.url.path,
            "method": request.method,
            "statusCode": 500,
            "latencyMs": latency_ms,
            "error": str(e)
        }
        logger.error(log_entry)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "traceId": trace_id
            }
        )

from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    
    # If detail is already a dict matching our shape, use it directly
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
        
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": str(exc.detail),
            "traceId": trace_id
        }
    )

# Global exception handler for any unhandled exceptions to ensure traceId is returned
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": str(exc),
            "traceId": trace_id
        }
    )
