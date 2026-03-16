"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.dependencies import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load settings and configure app on startup."""
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
