import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    # Spotify OAuth Configuration
    spotify_client_id: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
    spotify_client_secret: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri: str = os.getenv(
        "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/callback"
    )

    # Application Configuration
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # AI Agent Configuration
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    # LangSmith tracing configuration
    langsmith_api_key: Optional[str] = os.getenv("LANGSMITH_API_KEY")
    langsmith_project: Optional[str] = os.getenv(
        "LANGSMITH_PROJECT", "spotify-ai-playlist-generator"
    )
    langsmith_tracing_enabled: bool = (
        os.getenv("LANGSMITH_TRACING_ENABLED", "true").lower() == "true"
    )

    # Optional: Langfuse observability
    langfuse_public_key: Optional[str] = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: Optional[str] = os.getenv("LANGFUSE_SECRET_KEY")
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # Spotify OAuth URLs
    spotify_auth_url: str = "https://accounts.spotify.com/authorize"
    spotify_token_url: str = "https://accounts.spotify.com/api/token"
    spotify_user_url: str = "https://api.spotify.com/v1/me"

    class Config:
        case_sensitive = False

    def validate_required_settings(self):
        """Validate that required settings are present"""
        if not self.spotify_client_id:
            raise ValueError("SPOTIFY_CLIENT_ID is required")
        if not self.spotify_client_secret:
            raise ValueError("SPOTIFY_CLIENT_SECRET is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")


# Global settings instance
settings = Settings()
