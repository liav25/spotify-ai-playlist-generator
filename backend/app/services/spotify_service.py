"""
Spotify service for managing the dedicated service account
"""

import logging
from typing import Optional, Dict, Any
import spotipy

from .token_manager import spotify_token_manager

logger = logging.getLogger(__name__)

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

    async def get_client(self) -> spotipy.Spotify:
        """Get authenticated Spotify client for service account"""
        access_token = await spotify_token_manager.get_valid_token()
        
        # Create new client if needed or token changed
        if not self._client or self._current_token != access_token:
            self._client = spotipy.Spotify(auth=access_token)
            self._current_token = access_token
            logger.debug("Created Spotify client with refreshed token")
        
        return self._client

    async def get_client_with_retry(self, max_retries: int = 2) -> spotipy.Spotify:
        """Get authenticated Spotify client with automatic retry on auth failures"""
        for attempt in range(max_retries + 1):
            try:
                client = await self.get_client()
                # Test with a simple API call to ensure the token works
                client.current_user()
                return client
            except Exception as e:
                if "401" in str(e) or "403" in str(e):
                    if attempt < max_retries:
                        logger.warning(
                            f"Auth error on attempt {attempt + 1}, forcing token refresh and retrying..."
                        )
                        # Force refresh through token manager
                        await spotify_token_manager.force_refresh()
                        self._client = None  # Clear client to force recreation
                        continue
                    else:
                        logger.error(f"Auth failed after {max_retries + 1} attempts")
                        raise
                else:
                    # Non-auth error, don't retry
                    raise

    async def _validate_token_scopes(self, token_scope: str) -> None:
        """Validate that the access token has all required scopes"""
        if not token_scope:
            logger.warning("Cannot validate scopes - no scope information available")
            return

        # Parse the scope string into a set
        granted_scopes = set(scope.strip() for scope in token_scope.split())

        # Check for missing scopes
        missing_scopes = REQUIRED_SCOPES - granted_scopes

        if missing_scopes:
            logger.error(
                f"Access token is missing required scopes: {', '.join(missing_scopes)}"
            )
            logger.error(f"Granted scopes: {', '.join(granted_scopes)}")
            logger.error(f"Required scopes: {', '.join(REQUIRED_SCOPES)}")
            logger.error(
                "Please regenerate your refresh token with all required scopes."
            )

            raise Exception(
                f"Insufficient token scopes. Missing: {', '.join(missing_scopes)}. "
                "Please regenerate your refresh token using the generate_refresh_token.py script."
            )
        else:
            logger.info(f"Token has all required scopes: {', '.join(granted_scopes)}")

    async def validate_service_account(self) -> Dict[str, Any]:
        """Validate the service account configuration and return user info"""
        try:
            client = await self.get_client()
            user_info = client.current_user()

            return {
                "status": "valid",
                "user_id": user_info.get("id"),
                "display_name": user_info.get("display_name"),
                "email": user_info.get("email"),
                "country": user_info.get("country"),
                "followers": user_info.get("followers", {}).get("total", 0),
                "product": user_info.get("product", "unknown"),
            }
        except Exception as e:
            logger.error(f"Service account validation failed: {e}")
            return {
                "status": "invalid",
                "error": str(e),
                "message": "Service account validation failed. Please check your configuration.",
            }


# Global service client instance
spotify_service = SpotifyServiceClient()
