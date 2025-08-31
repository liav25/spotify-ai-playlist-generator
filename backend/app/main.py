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
from .routers import auth, api, chat
from .services.spotify_service import spotify_service

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    try:
        # Validate basic configuration
        settings.validate_required_settings()
        logger.info("✅ Configuration validation passed")
        
        # Validate Spotify service account
        logger.info("🔄 Validating Spotify service account...")
        service_validation = await spotify_service.validate_service_account()
        
        if service_validation["status"] == "valid":
            user_info = service_validation
            logger.info(f"✅ Spotify service account validated: {user_info['display_name']} ({user_info['user_id']})")
            logger.info(f"📊 Account details: {user_info['product']} subscription, {user_info['followers']} followers")
        else:
            logger.error(f"❌ Spotify service account validation failed: {service_validation['error']}")
            logger.error("🔧 To fix this issue:")
            logger.error("   1. Run: python generate_refresh_token.py")
            logger.error("   2. Follow the instructions to get a new refresh token")
            logger.error("   3. Update your .env file with the new SPOTIFY_SERVICE_REFRESH_TOKEN")
            logger.error("   4. Restart the application")
            
            # Don't fail startup, but warn about limited functionality
            logger.warning("⚠️  Application started with limited Spotify functionality")
        
        logger.info("🚀 Application started successfully")
        
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise
        
    yield
    
    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title="Mr. DJ",
    description="FastAPI backend with LangGraph agent for Spotify playlist creation by Mr. DJ",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - Allow both development and production origins
allowed_origins = [settings.frontend_url]

# In production, you might want to allow multiple origins or use a pattern
# For now, we'll be explicit about allowed origins
if "localhost" not in settings.frontend_url:
    # Production mode - add common development origins for testing
    allowed_origins.extend([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(api.router, prefix="/api", tags=["api"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

# Include callback route at root level for Spotify OAuth
from .routers.auth import spotify_callback
app.get("/callback")(spotify_callback)

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
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/spotify-status")
async def spotify_status():
    """Check Spotify service account status"""
    service_validation = await spotify_service.validate_service_account()
    
    if service_validation["status"] == "valid":
        return {
            "status": "operational",
            "user": {
                "id": service_validation["user_id"],
                "display_name": service_validation["display_name"],
                "product": service_validation["product"],
                "country": service_validation["country"]
            },
            "message": "Spotify service account is working correctly"
        }
    else:
        return {
            "status": "error",
            "error": service_validation["error"],
            "message": service_validation["message"],
            "fix_instructions": [
                "Run: python generate_refresh_token.py",
                "Follow the authorization flow",
                "Update .env with new SPOTIFY_SERVICE_REFRESH_TOKEN",
                "Restart the application"
            ]
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
