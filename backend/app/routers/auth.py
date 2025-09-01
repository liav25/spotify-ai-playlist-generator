"""
Authentication router for service account setup
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..services.spotify_service import spotify_service
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/setup")
async def setup_service_account():
    """Get authorization URL for service account setup"""
    try:
        auth_url = spotify_service.get_authorization_url()
        logger.info("Generated authorization URL for service account setup")

        return {
            "status": "success",
            "auth_url": auth_url,
            "instructions": [
                "Visit the authorization URL",
                "Login with your Spotify account (the service account)",
                "Complete the authorization",
                "You'll be redirected back automatically",
            ],
        }
    except Exception as e:
        logger.error(f"Failed to generate setup URL: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate authorization URL"
        )


@router.get("/callback")
async def auth_callback(
    code: str = Query(None), error: str = Query(None), state: str = Query(None)
):
    """Handle Spotify OAuth callback for service account"""
    if error:
        logger.error(f"OAuth error: {error}")
        return RedirectResponse(url=f"{settings.frontend_url}?setup_error=oauth_denied")

    if not code:
        logger.error("No authorization code received")
        return RedirectResponse(url=f"{settings.frontend_url}?setup_error=no_code")

    try:
        # Build the full response URL that Spotipy expects
        # The response URL should match what Spotify redirected to
        response_url = f"{settings.spotify_redirect_uri}?code={code}"
        if state:
            response_url += f"&state={state}"

        logger.info(f"Processing authorization callback with code: {code[:10]}...")

        # Handle the authorization response
        result = spotify_service.handle_authorization_response(response_url)

        if result["status"] == "success":
            logger.info("Service account authentication completed successfully")
            return RedirectResponse(url=f"{settings.frontend_url}?setup=success")
        else:
            logger.error(f"Authorization handling failed: {result['message']}")
            return RedirectResponse(
                url=f"{settings.frontend_url}?setup_error=auth_failed"
            )

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}?setup_error=callback_error"
        )


@router.get("/status")
async def auth_status():
    """Check service account authentication status"""
    service_validation = await spotify_service.validate_service_account()

    return {
        "authenticated": service_validation["status"] == "valid",
        "service_account": service_validation,
        "requires_setup": service_validation.get("requires_auth", False),
    }


@router.post("/refresh")
async def refresh_service_account():
    """Force refresh the service account token"""
    try:
        # Clear the current client to force token refresh on next request
        spotify_service._spotify_client = None

        # Validate to trigger refresh
        service_validation = await spotify_service.validate_service_account()

        return {
            "status": "success" if service_validation["status"] == "valid" else "error",
            "service_account": service_validation,
        }
    except Exception as e:
        logger.error(f"Failed to refresh service account: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh service account")
