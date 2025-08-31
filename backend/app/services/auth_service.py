"""
Authentication service for user session management
"""

from typing import Optional
from fastapi import Request

from ..api.models import User


async def get_current_user_from_header(request: Request) -> Optional[User]:
    """Get current user from Authorization header"""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None

    # Extract the token (this would be the Spotify access token from frontend)
    token = authorization.replace("Bearer ", "")

    # Find user session by looking for matching token
    for session_data in user_sessions.values():
        if session_data.get("frontend_token") == token:
            return session_data["user"]

    return None
