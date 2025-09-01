"""
Spotify service for managing the dedicated service account
"""

import logging
import os
from typing import Optional, Dict, Any
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from spotipy.cache_handler import RedisCacheHandler

logger = logging.getLogger(__name__)
from dotenv import load_dotenv

load_dotenv("/Users/liavalter/Projects/test_spotify/backend/.env")

# Required scopes for the service to function properly
REQUIRED_SCOPES = {
    # User profile and account access
    "user-read-private",
    "user-read-email",
    # Playlist management
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    # Music discovery and personalization
    "user-library-read",
    "user-library-modify",
    "user-top-read",
    "user-read-recently-played",
    "user-read-playback-state",
    "user-read-currently-playing",
    # Social features
    "user-follow-read",
    "user-follow-modify",
    # Streaming (if needed for previews)
    "streaming",
    "app-remote-control",
    # Images
    "ugc-image-upload",
}


class SpotifyServiceClient:
    """Manages Spotify client for the dedicated service account"""

    def __init__(self):
        self._client: Optional[spotipy.Spotify] = None
        self._current_token: Optional[str] = None

    async def _build_client(self) -> spotipy.Spotify:
        """Instantiate a Spotipy client and save it on the instance."""
        import redis

        redis_client = redis.from_url(
            os.getenv("REDIS_URL"),
            decode_responses=True,
        )
        cache_handler = RedisCacheHandler(redis_client)
        sp_oauth = SpotifyOAuth(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
            scope="user-read-email user-library-read playlist-modify-private playlist-modify-public",
        )

        # Manually provide the refresh token on startup (for Spotipy 2.23+)
        token_info = {
            "refresh_token": os.environ["SPOTIFY_REFRESH_TOKEN"],
            "scope": "user-read-email user-library-read playlist-modify-private playlist-modify-public",
            "expires_at": 0,  # Forces refresh on first use
        }
        sp_oauth.cache_handler.save_token_to_cache(token_info)

        self._client = spotipy.Spotify(auth_manager=sp_oauth)
        return self._client

    async def get_client(self) -> spotipy.Spotify:
        """Return a cached client; build it once if necessary."""
        if self._client is None:  # ← use the cache
            await self._build_client()
        return self._client


# Global service client instance
spotify_service = SpotifyServiceClient()
