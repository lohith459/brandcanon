import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.config import settings
from app.database import engine, init_db
from app.seed.seed_data import seed_canon_data
from app.api.health import router as health_router
from app.api.submissions import router as submissions_router
from app.api.review import router as review_router
from app.api.workflow import router as workflow_router
from app.api.tools import router as tools_router
from app.api.canon import router as canon_router

# In-memory rate limiter: tracks timestamps per client IP
rate_limit_records = defaultdict(list)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: initialize tables and seed brand canon data."""
    init_db()
    with Session(engine) as session:
        seed_canon_data(session)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent brand-governance platform for pre-publication content review.",
    lifespan=lifespan
)

# Simple in-memory rate limiting middleware
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    # Only rate limit API state-changing or review operations
    if request.url.path.startswith("/api/submissions") and request.method in ("POST", "PUT"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        # Clean older than 60 seconds
        rate_limit_records[client_ip] = [t for t in rate_limit_records[client_ip] if now - t < 60]
        if len(rate_limit_records[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please wait before submitting more content."}
            )
        rate_limit_records[client_ip].append(now)
    
    response: Response = await call_next(request)
    return response

# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Include API routers
app.include_router(health_router)
app.include_router(submissions_router)
app.include_router(review_router)
app.include_router(workflow_router)
app.include_router(tools_router)
app.include_router(canon_router)

# Static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def get_root():
    """Serves the main application page."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "health": "/health",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
