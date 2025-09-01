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
from .services.token_manager import spotify_token_manager

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

        # Initialize and test Redis connection
        if settings.redis_enabled:
            logger.info("🔄 Testing Redis connection for token management...")
            token_health = await spotify_token_manager.health_check()
            if token_health["status"] == "healthy":
                if token_health.get("redis_status") == "connected":
                    logger.info("✅ Redis connection established for token caching")
                else:
                    logger.warning("⚠️  Redis unavailable, using direct token refresh fallback")
            else:
                logger.error(f"❌ Token manager health check failed: {token_health.get('error')}")
        else:
            logger.info("ℹ️  Redis disabled, using direct token refresh")

        # Proactively refresh and validate Spotify service account
        logger.info("🔄 Proactively refreshing and validating Spotify service account...")
        
        try:
            # Force a token refresh on startup to handle any token issues immediately
            logger.info("🔄 Refreshing access token proactively...")
            await spotify_token_manager.get_valid_token()  # This will refresh if needed
            
            # Now validate the service account
            service_validation = await spotify_service.validate_service_account()
            
            if service_validation["status"] == "valid":
                user_info = service_validation
                logger.info(
                    f"✅ Spotify service account validated: {user_info['display_name']} ({user_info['user_id']})"
                )
                logger.info(
                    f"📊 Account details: {user_info['product']} subscription, {user_info['followers']} followers"
                )
                logger.info("🎯 Service account ready for 24/7 operation!")
            else:
                logger.error(
                    f"❌ Spotify service account validation failed: {service_validation['error']}"
                )
                raise Exception(f"Service account validation failed: {service_validation['error']}")
                
        except Exception as e:
            logger.error(f"❌ Spotify service account setup failed: {e}")
            logger.error("🔧 To fix this issue:")
            logger.error("   1. Visit: http://127.0.0.1:8000/auth/setup")
            logger.error("   2. Complete the one-time OAuth setup")
            logger.error("   3. Restart the application")
            
            # Don't fail startup completely, but log the setup URL
            logger.warning("⚠️  Application started with limited Spotify functionality")
            logger.warning(f"🔗 Setup URL: http://127.0.0.1:8000/auth/setup")

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
app.include_router(auth.router, prefix="/auth", tags=["service-account"])
app.include_router(api.router, prefix="/api", tags=["api"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

# Include OAuth callback for one-time setup
from .routers.auth import oauth_callback

app.get("/auth/callback")(oauth_callback)


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
                "country": service_validation["country"],
            },
            "message": "Spotify service account is working correctly",
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
                "Restart the application",
            ],
        }


@app.get("/api/token-metrics")
async def token_metrics():
    """Get token management metrics for monitoring"""
    metrics = await spotify_token_manager.get_metrics()
    health = await spotify_token_manager.health_check()
    
    return {
        "metrics": metrics,
        "health": health,
        "message": "Token management system metrics"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
