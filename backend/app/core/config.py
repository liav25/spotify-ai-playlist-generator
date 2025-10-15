import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    # Spotify App Configuration (for service account only)
    spotify_client_id: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
    spotify_client_secret: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")

    # Service Account Configuration (Your Dedicated Account)
    spotify_service_refresh_token: Optional[str] = os.getenv(
        "SPOTIFY_SERVICE_REFRESH_TOKEN"
    )
    spotify_service_user_id: Optional[str] = os.getenv("SPOTIFY_SERVICE_USER_ID")

    # Application Configuration
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # AI Agent Configuration
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    openrouter_model: str = os.getenv(
        "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"
    )
    ultrathink_openrouter_model: Optional[str] = os.getenv(
        "ULTRATHINK_OPENROUTER_MODEL"
    )
    openrouter_base_url: str = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    openrouter_referer: Optional[str] = os.getenv("OPENROUTER_SITE_URL")
    openrouter_title: Optional[str] = os.getenv("OPENROUTER_SITE_NAME")
    tavily_api_key: Optional[str] = os.getenv("TAVILY_API_KEY")

    # LangSmith tracing configuration
    langsmith_api_key: Optional[str] = os.getenv("LANGSMITH_API_KEY")
    langsmith_project: Optional[str] = os.getenv(
        "LANGSMITH_PROJECT", "spotify-ai-playlist-generator"
    )
    langsmith_tracing_enabled: bool = (
        os.getenv("LANGSMITH_TRACING_ENABLED", "true").lower() == "true"
    )

    # Redis Configuration for token caching
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_enabled: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"

    # Spotify API URLs
    spotify_token_url: str = "https://accounts.spotify.com/api/token"

    class Config:
        case_sensitive = False

    def validate_required_settings(self):
        """Validate that required settings are present"""
        if not self.spotify_client_id:
            raise ValueError("SPOTIFY_CLIENT_ID is required")
        if not self.spotify_client_secret:
            raise ValueError("SPOTIFY_CLIENT_SECRET is required")
        if not self.spotify_service_refresh_token:
            raise ValueError("SPOTIFY_SERVICE_REFRESH_TOKEN is required")
        if not self.spotify_service_user_id:
            raise ValueError("SPOTIFY_SERVICE_USER_ID is required")
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required")


# Global settings instance
settings = Settings()
