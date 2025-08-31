"""
API router for user and playlist endpoints
"""

import logging
import spotipy
from fastapi import APIRouter, HTTPException, status, Request

from ..api.models import User, PlaylistData
from ..services.auth_service import get_current_user_from_header

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/user", response_model=User)
async def get_user(request: Request):
    """Get current user information"""
    current_user = await get_current_user_from_header(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return current_user


@router.get("/playlist/{playlist_id}", response_model=PlaylistData)
async def get_playlist(playlist_id: str, request: Request):
    """Get playlist information with tracks and album covers"""
    current_user = await get_current_user_from_header(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        # Get user session to retrieve Spotify token
        user_session = user_sessions.get(current_user.id)
        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found"
            )

        spotify_token = user_session.get("spotify_token")
        if not spotify_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spotify token not available",
            )

        # Create Spotify client with user's token
        spotify_client = spotipy.Spotify(auth=spotify_token)

        # Use the get_playlist_tracks tool
        from ..langgraph.tools import get_playlist_tracks

        config = {"configurable": {"spotify_client": spotify_client}}

        playlist_data = get_playlist_tracks.invoke(
            {"playlist_id": playlist_id, "limit": 100}, config
        )

        if not playlist_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found"
            )

        return PlaylistData(**playlist_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching playlist {playlist_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch playlist: {str(e)}",
        )
