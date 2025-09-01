"""
Service Account Setup & Status - One-time OAuth + 24/7 Operation
"""

import os
import secrets
import base64
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx

from ..core.config import settings
from ..services.spotify_service import spotify_service

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for OAuth state (only during setup)
_setup_state = {}

# Required scopes for service account
REQUIRED_SCOPES = [
    "user-read-private",
    "user-read-email", 
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-library-read",
    "user-library-modify",
    "user-top-read",
    "user-read-recently-played",
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-follow-read",
    "user-follow-modify",
    "streaming",
    "app-remote-control",
    "ugc-image-upload",
]


@router.get("/status")
async def auth_status():
    """Check service account authentication status"""
    service_validation = await spotify_service.validate_service_account()
    
    if service_validation["status"] == "valid":
        return {
            "mode": "service_account", 
            "status": "authenticated",
            "service_user": {
                "id": service_validation["user_id"],
                "display_name": service_validation["display_name"],
                "product": service_validation["product"]
            },
            "message": "Service account is operational - no user login required"
        }
    else:
        return {
            "mode": "service_account",
            "status": "needs_setup", 
            "error": service_validation["error"],
            "setup_url": f"{settings.backend_url}/auth/setup",
            "message": "Visit /auth/setup to configure your Spotify service account"
        }


@router.get("/setup", response_class=HTMLResponse)
async def setup_page():
    """One-time setup page for service account OAuth"""
    
    # Check if already configured
    service_validation = await spotify_service.validate_service_account()
    if service_validation["status"] == "valid":
        return HTMLResponse(f"""
        <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1>✅ Service Account Already Configured</h1>
            <p><strong>Account:</strong> {service_validation['display_name']} ({service_validation['user_id']})</p>
            <p><strong>Product:</strong> {service_validation['product']}</p>
            <p>Your Spotify service account is working correctly!</p>
            <a href="/api/spotify-status" style="color: #1db954;">Check API Status</a>
        </body></html>
        """)
    
    # Generate secure state for OAuth
    state = secrets.token_urlsafe(32)
    _setup_state["current"] = state
    
    # Build Spotify OAuth URL
    scope_string = " ".join(REQUIRED_SCOPES)
    redirect_uri = f"{settings.backend_url}/auth/callback"
    
    oauth_url = (
        f"https://accounts.spotify.com/authorize"
        f"?response_type=code"
        f"&client_id={settings.spotify_client_id}"
        f"&scope={scope_string}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&show_dialog=true"
    )
    
    return HTMLResponse(f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
        <h1>🎵 Spotify Service Account Setup</h1>
        <p>This is a <strong>one-time setup</strong> to connect your Spotify account for 24/7 playlist creation.</p>
        
        <div style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>What happens next:</h3>
            <ol>
                <li>Click "Connect Spotify Account" below</li>
                <li>Authorize the application on Spotify</li>
                <li>Your refresh token will be saved automatically</li>
                <li>The service will run 24/7 using your account</li>
            </ol>
        </div>
        
        <a href="{oauth_url}" style="
            display: inline-block; 
            background: #1db954; 
            color: white; 
            padding: 15px 30px; 
            text-decoration: none; 
            border-radius: 25px;
            font-weight: bold;
        ">🔗 Connect Spotify Account</a>
        
        <p style="color: #666; font-size: 0.9em; margin-top: 30px;">
            <strong>Note:</strong> This setup uses your personal Spotify account. All website users will create playlists on your account.
        </p>
    </body></html>
    """)


@router.get("/callback")
async def oauth_callback(code: str, state: str):
    """Handle OAuth callback and save refresh token"""
    
    # Verify state parameter
    if state != _setup_state.get("current"):
        raise HTTPException(status_code=400, detail="Invalid state parameter - possible CSRF attack")
    
    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            # Prepare token request
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{settings.backend_url}/auth/callback",
            }
            
            # Basic auth header
            credentials = base64.b64encode(
                f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            # Request tokens
            response = await client.post(
                "https://accounts.spotify.com/api/token", 
                data=token_data, 
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code")
            
            token_response = response.json()
            refresh_token = token_response.get("refresh_token")
            access_token = token_response.get("access_token")
            
            if not refresh_token:
                raise HTTPException(status_code=400, detail="No refresh token received")
            
            # Get user info to verify
            user_response = await client.get(
                "https://api.spotify.com/v1/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user information")
            
            user_data = user_response.json()
            user_id = user_data["id"]
            display_name = user_data.get("display_name", user_id)
            
            # Save tokens to .env file
            await _update_env_file(refresh_token, user_id)
            
            # Clear setup state
            _setup_state.clear()
            
            return HTMLResponse(f"""
            <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1>✅ Setup Complete!</h1>
                <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Service Account Connected:</h3>
                    <p><strong>Name:</strong> {display_name}</p>
                    <p><strong>User ID:</strong> {user_id}</p>
                    <p><strong>Product:</strong> {user_data.get('product', 'Unknown')}</p>
                </div>
                
                <p>Your refresh token has been saved and the service is now ready for 24/7 operation!</p>
                
                <a href="/api/spotify-status" style="
                    display: inline-block; 
                    background: #1db954; 
                    color: white; 
                    padding: 10px 20px; 
                    text-decoration: none; 
                    border-radius: 5px;
                ">Test API Status</a>
            </body></html>
            """)
    
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


async def _update_env_file(refresh_token: str, user_id: str):
    """Update .env file with new refresh token"""
    env_path = ".env"
    
    # Read current .env content
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add the tokens
    refresh_token_updated = False
    user_id_updated = False
    
    for i, line in enumerate(env_lines):
        if line.startswith("SPOTIFY_SERVICE_REFRESH_TOKEN="):
            env_lines[i] = f"SPOTIFY_SERVICE_REFRESH_TOKEN={refresh_token}\n"
            refresh_token_updated = True
        elif line.startswith("SPOTIFY_SERVICE_USER_ID="):
            env_lines[i] = f"SPOTIFY_SERVICE_USER_ID={user_id}\n"  
            user_id_updated = True
    
    # Add tokens if they weren't found
    if not refresh_token_updated:
        env_lines.append(f"SPOTIFY_SERVICE_REFRESH_TOKEN={refresh_token}\n")
    if not user_id_updated:
        env_lines.append(f"SPOTIFY_SERVICE_USER_ID={user_id}\n")
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.writelines(env_lines)
    
    logger.info(f"Updated .env file with new refresh token for user {user_id}")
