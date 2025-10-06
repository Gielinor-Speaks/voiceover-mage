# ABOUTME: FastAPI application entry point for NPC voice generation API
# ABOUTME: Provides REST endpoints mirroring CLI functionality

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from voiceover_mage.api.dependencies import get_db_manager
from voiceover_mage.api.routes import generation, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler for startup/shutdown."""
    # Startup: Initialize database tables
    db_manager = get_db_manager()
    await db_manager.create_tables()

    yield

    # Shutdown: Close database connections
    await db_manager.close()


app = FastAPI(
    title="Voiceover Mage API",
    description="AI voice generation system for Old School RuneScape NPCs",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for browser-based clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route handlers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(generation.router, prefix="/api/v1", tags=["Voice Generation"])
