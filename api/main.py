"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.dependencies import get_settings
from api.routes.content import router as content_router
from api.routes.generate import router as generate_router
from api.routes.health import router as health_router
from api.routes.iterate import router as iterate_router
from api.routes.postiz import router as postiz_router
from api.routes.settings import router as settings_router
from api.routes.templates import router as templates_router
from api.routes.pillars import router as pillars_router
from api.routes.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load settings and configure app on startup."""
    settings = get_settings()
    if settings.demo_mode:
        print("\n  ** DEMO MODE ACTIVE — using sample Gita Valley data **\n")
    yield


app = FastAPI(
    title="Gita Valley Content Engine API",
    version="0.1.0",
    description="Backend API for the Gita Valley social media content platform.",
    lifespan=lifespan,
)


def _configure_cors() -> None:
    """Add CORS middleware using current settings."""
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_configure_cors()

app.include_router(auth_router)
app.include_router(content_router)
app.include_router(generate_router)
app.include_router(iterate_router)
app.include_router(templates_router)
app.include_router(settings_router)
app.include_router(pillars_router)
app.include_router(postiz_router)
app.include_router(health_router)
app.include_router(upload_router)


@app.get("/")
async def root():
    """API info endpoint."""
    return {
        "name": "Gita Valley Content Engine API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Basic health check."""
    return {"status": "healthy"}
