"""
Authentication router for Spotify OAuth flow
"""

import secrets
import base64
import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from ..core.config import settings
from ..api.models import User, SpotifyTokenResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_random_string(length: int = 32) -> str:
    """Generate random string for state parameter"""
    return secrets.token_urlsafe(length)


@router.get("/login")
async def spotify_login():
    """Initiate Spotify OAuth flow"""
    # Generate state parameter for security
    state = generate_random_string()

    # Store state for verification (in production, use Redis/database)
    user_sessions[state] = {"state": state, "timestamp": datetime.now(timezone.utc)}

    # Build authorization URL
    auth_params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "state": state,
        "scope": "user-read-private user-read-email playlist-modify-public playlist-modify-private playlist-read-private",
        "show_dialog": "false",
    }

    # Construct URL
    auth_url = f"{settings.spotify_auth_url}?"
    auth_url += "&".join([f"{k}={v}" for k, v in auth_params.items()])

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def spotify_callback(code: str, state: str):
    """Handle Spotify OAuth callback"""
    # Verify state parameter
    if state not in user_sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter"
        )

    # Exchange authorization code for access token
    async with httpx.AsyncClient() as client:
        # Prepare token request
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.spotify_redirect_uri,
        }

        # Basic auth header
        credentials = base64.b64encode(
            f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Request token
        response = await client.post(
            settings.spotify_token_url, data=token_data, headers=headers
        )

        if response.status_code != 200:
            logger.error(f"Spotify token request failed: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code",
            )

        token_response = SpotifyTokenResponse(**response.json())

        # Get user information
        user_headers = {"Authorization": f"Bearer {token_response.access_token}"}

        user_response = await client.get(
            settings.spotify_user_url, headers=user_headers
        )

        if user_response.status_code != 200:
            logger.error(f"Spotify user request failed: {user_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information",
            )

        user_data = user_response.json()
        user = User(
            id=user_data["id"],
            display_name=user_data["display_name"],
            email=user_data.get("email"),
            images=user_data.get("images"),
        )

        # Generate a simple session token
        session_token = generate_random_string(32)

        # Store user session with Spotify token
        user_sessions[user.id] = {
            "user": user,
            "spotify_token": token_response.access_token,
            "frontend_token": session_token,
            "token_expires_at": datetime.now(timezone.utc)
            + timedelta(seconds=token_response.expires_in),
        }

        # Clean up state
        if state in user_sessions:
            del user_sessions[state]

        # Redirect to frontend with simple session token
        redirect_url = f"{settings.frontend_url}?token={session_token}"
        return RedirectResponse(url=redirect_url)
