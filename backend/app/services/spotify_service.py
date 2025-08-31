"""
Spotify service for managing the dedicated service account
"""

import logging
import base64
import asyncio
import time
from typing import Optional, List, Dict, Any
import httpx
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from ..core.config import settings

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
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None

    async def get_client(self) -> spotipy.Spotify:
        """Get authenticated Spotify client for service account"""
        if not self._client or not await self._is_token_valid():
            await self._refresh_client()
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
                            f"Auth error on attempt {attempt + 1}, forcing refresh and retrying..."
                        )
                        # Force refresh by clearing current client
                        self._client = None
                        self._access_token = None
                        self._token_expires_at = None
                        continue
                    else:
                        logger.error(f"Auth failed after {max_retries + 1} attempts")
                        raise
                else:
                    # Non-auth error, don't retry
                    raise

    async def _is_token_valid(self) -> bool:
        """Check if current access token is still valid"""
        if not self._client or not self._access_token:
            return False

        # Proactive token refresh - check if token expires within 10 minutes
        if self._token_expires_at and time.time() >= (self._token_expires_at - 600):
            logger.info("🔄 Access token expires soon, proactively refreshing...")
            return False

        try:
            # Test the token by making a simple API call
            user_info = self._client.current_user()
            logger.debug(f"Token validation successful for user: {user_info.get('id')}")
            return True
        except Exception as e:
            # Enhanced error logging with specific handling for different scenarios
            error_str = str(e)
            if "401" in error_str:
                logger.info(f"Token expired (HTTP 401), will refresh: {e}")
            elif "403" in error_str:
                if "user may not be registered" in error_str.lower():
                    logger.error(
                        f"Token lacks required scopes or app configuration issue (HTTP 403): {e}"
                    )
                    logger.error(
                        "This usually means the refresh token was generated without proper scopes."
                    )
                    logger.error(f"Required scopes: {', '.join(REQUIRED_SCOPES)}")
                else:
                    logger.warning(f"Access forbidden (HTTP 403): {e}")
            elif "429" in error_str:
                logger.warning(f"Rate limited (HTTP 429): {e}")
            else:
                logger.debug(f"Token validation failed with unexpected error: {e}")
            return False

    async def _refresh_client(self) -> None:
        """Refresh the Spotify client using the service account refresh token"""
        max_retries = 3
        base_delay = 1.0  # seconds

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Refreshing service account Spotify client (attempt {attempt + 1}/{max_retries})"
                )

                # Use refresh token to get new access token
                token_data = await self._get_access_token_from_refresh()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise Exception("No access token received from refresh")

                # Create new Spotify client and track expiration
                self._access_token = access_token
                self._client = spotipy.Spotify(auth=access_token)

                # Track token expiration (Spotify tokens expire in 1 hour = 3600 seconds)
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in
                logger.debug(
                    f"Token will expire at: {time.ctime(self._token_expires_at)}"
                )

                # Verify client works and validate scopes
                user_info = self._client.current_user()

                # Check if we have scope information in the token response
                token_scope = token_data.get("scope", "")
                if token_scope:
                    await self._validate_token_scopes(token_scope)
                else:
                    logger.warning("No scope information received in token response")

                logger.info(
                    f"Service account client refreshed for user: {user_info.get('display_name')} ({user_info.get('id')})"
                )
                return  # Success, exit retry loop

            except Exception as e:
                is_last_attempt = attempt == max_retries - 1
                if is_last_attempt:
                    logger.error(
                        f"Failed to refresh service account client after {max_retries} attempts: {e}"
                    )
                    # Clear the invalid client
                    self._client = None
                    self._access_token = None
                    self._token_expires_at = None
                    raise
                else:
                    # Exponential backoff for retries
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Refresh attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)

    async def _get_access_token_from_refresh(self) -> Dict[str, Any]:
        """Exchange refresh token for access token and return full response"""
        if not settings.spotify_service_refresh_token:
            raise ValueError("SPOTIFY_SERVICE_REFRESH_TOKEN not configured")

        async with httpx.AsyncClient() as client:
            # Prepare token refresh request (using only Basic auth, not client_id in body)
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": settings.spotify_service_refresh_token,
            }

            # Basic auth header
            credentials = base64.b64encode(
                f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
            ).decode()

            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            # Request new access token
            response = await client.post(
                settings.spotify_token_url, data=token_data, headers=headers
            )

            if response.status_code != 200:
                logger.error(
                    f"Token refresh failed: Status {response.status_code}, Body: {response.text}"
                )

                # Handle specific error cases
                if response.status_code == 400:
                    logger.error("❌ Bad request - likely invalid refresh token")
                    logger.error(
                        "💡 SOLUTION: Run 'python generate_refresh_token.py' to get a new refresh token"
                    )
                elif response.status_code == 401:
                    logger.error("❌ Unauthorized - check client credentials")

                raise Exception(
                    f"Failed to refresh access token: {response.status_code}"
                )

            token_response = response.json()
            access_token = token_response.get("access_token")

            if not access_token:
                logger.error(f"No access token in response: {token_response}")
                raise Exception("No access token in refresh response")

            # Check if we got a new refresh token (optional but good practice)
            new_refresh_token = token_response.get("refresh_token")
            if new_refresh_token:
                logger.warning(
                    "🔄 Received new refresh token - you should update your SPOTIFY_SERVICE_REFRESH_TOKEN environment variable"
                )
                logger.warning(f"New refresh token: {new_refresh_token}")
                # Note: In production, you'd want to automatically update this in your config store

            # Log scope information if available
            scope = token_response.get("scope", "")
            if scope:
                logger.debug(f"Token scopes: {scope}")
            else:
                logger.warning("No scope information in token response")

            logger.debug("Successfully obtained new access token")
            return token_response

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
