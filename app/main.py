"""
Ekodi - Main FastAPI application entry point.

Serves the React frontend (production build) and all API routes.
Includes load protection middleware for server health monitoring.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import auth, chat, tts, api_v1, feedback, admin
from app.middleware.load_protection import LoadProtectionMiddleware
from app.services.server_monitor import get_monitor

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

FRONTEND_BUILD = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    logger.info("Ekodi platform starting...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Ekodi platform shutting down")


app = FastAPI(
    title="Ekodi - Bambara Voice AI Platform",
    description="Interactive Voice AI for Bambara (Bamanankan)",
    version="1.0.0",
    lifespan=lifespan,
)

# Load protection middleware (must be added before CORS)
app.add_middleware(LoadProtectionMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Server-Status", "Retry-After"],
)

# API routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(api_v1.router)
app.include_router(feedback.router)
app.include_router(admin.router)


# ── Public Health Check ──────────────────────────────────────

@app.get("/health")
async def health():
    """Lightweight health check (for Docker, load balancers, uptime monitors)."""
    monitor = get_monitor()
    status_level = monitor.get_status_level()
    return {
        "status": status_level,
        "version": settings.APP_VERSION,
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }


@app.get("/status")
async def public_status():
    """Public status endpoint — tells clients if the server can accept requests."""
    monitor = get_monitor()
    stats = monitor.get_stats()
    return {
        "status": monitor.get_status_level(),
        "can_accept_requests": not stats.is_overloaded,
        "active_requests": stats.active_requests,
        "cpu_percent": stats.cpu_percent,
        "memory_percent": stats.memory_percent,
        "avg_response_time_ms": stats.avg_response_time_ms,
    }


# Serve React frontend (production build)
if FRONTEND_BUILD.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve static files from dist/ root, or fall back to index.html for SPA routing."""
        from fastapi.responses import FileResponse

        # First check if the path matches a real file in dist/ (logos, audio, etc.)
        if full_path:
            static_file = FRONTEND_BUILD / full_path
            if static_file.is_file():
                return FileResponse(str(static_file))

        # Otherwise serve index.html (React Router handles client-side routing)
        index = FRONTEND_BUILD / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"error": "Frontend not built. Run: cd frontend && npm run build"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
