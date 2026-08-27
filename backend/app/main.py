from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.health import router as health_router
from .routers.auth import router as auth_router
from .routers.profile import router as profile_router
from .routers.safety import router as safety_router
from .config import settings
from .middleware import (
    MaxBodySizeMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)

app = FastAPI(
    title="Smart Women Security Backend",
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Security/reliability middleware (order matters: outermost first).
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(safety_router, prefix="/api")
