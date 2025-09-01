"""
Simplified API router - Service Account Mode
All operations use the dedicated service account
"""

import logging
from fastapi import APIRouter, HTTPException, status

from backend.app.api.models import PlaylistData

from ..services.spotify_service import spotify_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/service-user")
async def get_service_user():
    """Get service account user information"""
    service_validation = await spotify_service.validate_service_account()

    if service_validation["status"] == "valid":
        return {
            "id": service_validation["user_id"],
            "display_name": service_validation["display_name"],
            "email": service_validation.get("email"),
            "country": service_validation.get("country"),
            "product": service_validation["product"],
            "followers": service_validation.get("followers", 0),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service account not available",
        )


@router.get("/playlist/{playlist_id}", response_model=PlaylistData)
async def get_playlist(playlist_id: str):
    """Get playlist information using service account"""
    try:
        # Use service account client
        spotify_client = await spotify_service.get_client_with_retry()

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
