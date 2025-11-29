#!/usr/bin/env python3
"""
Mr. DJ - FastAPI Backend
Handles Spotify OAuth authentication and LangGraph agent integration
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routers import api, chat

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Set specific loggers to appropriate levels
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

app = FastAPI(
    title="Mr. DJ",
    description="FastAPI backend with LangGraph agent for Spotify playlist creation by Mr. DJ",
    version="1.0.0",
)

# CORS middleware - Allow both development and production origins
allowed_origins = [settings.frontend_url]

# In production, you might want to allow multiple origins or use a pattern
# For now, we'll be explicit about allowed origins
if "localhost" not in settings.frontend_url:
    # Production mode - add common development origins for testing
    allowed_origins.extend(
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api.router, prefix="/api", tags=["api"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Mr. DJ API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy",
        "service": "spotify-ai-playlist-generator",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
