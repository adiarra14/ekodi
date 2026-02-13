"""
Ekodi - Main FastAPI application entry point.

Serves the React frontend (production build) and all API routes.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import auth, chat, tts, api_v1, feedback, admin

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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(api_v1.router)
app.include_router(feedback.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }


# Serve React frontend (production build)
if FRONTEND_BUILD.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes."""
        from fastapi.responses import FileResponse

        # Serve index.html for all routes (React Router handles client-side routing)
        index = FRONTEND_BUILD / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"error": "Frontend not built. Run: cd frontend && npm run build"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
