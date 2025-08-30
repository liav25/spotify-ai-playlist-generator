#!/usr/bin/env python3
"""
Mr. DJ - FastAPI Backend
Handles Spotify OAuth authentication and LangGraph agent integration
"""

import secrets
import base64
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import spotipy
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from langchain_core.messages import HumanMessage

from .core.config import settings
from .api.models import (
    ChatRequest,
    ChatResponse,
    User,
    SpotifyTokenResponse,
    PlaylistData,
)
from .langgraph.agent import assistant_ui_graph

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Set specific loggers to appropriate levels
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

# In-memory storage for demo (use database in production)
user_sessions = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    try:
        settings.validate_required_settings()
        logger.info("Application started successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    yield
    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title="Mr. DJ",
    description="FastAPI backend with LangGraph agent for Spotify playlist creation by Mr. DJ",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - Allow both development and production origins
allowed_origins = [settings.frontend_url]

# In production, you might want to allow multiple origins or use a pattern
# For now, we'll be explicit about allowed origins
if "localhost" not in settings.frontend_url:
    # Production mode - add common development origins for testing
    allowed_origins.extend([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def generate_random_string(length: int = 32) -> str:
    """Generate random string for state parameter"""
    return secrets.token_urlsafe(length)




@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Mr. DJ API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy",
        "service": "spotify-ai-playlist-generator",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/auth/login")
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


@app.get("/callback")
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


@app.get("/api/user", response_model=User)
async def get_user(request: Request):
    """Get current user information"""
    current_user = await get_current_user_from_header(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return current_user


@app.get("/api/playlist/{playlist_id}", response_model=PlaylistData)
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
        from .langgraph.tools import get_playlist_tracks

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



@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest, request: Request):
    """Chat endpoint that integrates with LangGraph agent"""
    current_user = await get_current_user_from_header(request)
    
    logger.info(
        f"🚀 Chat request received from user {current_user.id if current_user else 'None'}"
    )
    logger.debug(f"📝 Message: {chat_request.message}")
    logger.debug(f"🔗 Thread ID: {chat_request.thread_id}")

    if not current_user:
        logger.warning("❌ Authentication failed - no current user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        # Get user session to retrieve Spotify token
        logger.debug(f"🔍 Looking up user session for {current_user.id}")
        user_session = user_sessions.get(current_user.id)
        if not user_session:
            logger.error(f"❌ No session found for user {current_user.id}")
            logger.debug(f"Available sessions: {list(user_sessions.keys())}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found"
            )

        spotify_token = user_session.get("spotify_token")
        if not spotify_token:
            logger.error(
                f"❌ No Spotify token found in session for user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spotify token not available",
            )

        logger.debug(f"✅ Spotify token found, creating client")

        # Create Spotify client with user's token
        spotify_client = spotipy.Spotify(auth=spotify_token)

        # Test Spotify client
        try:
            user_info = spotify_client.current_user()
            logger.debug(
                f"✅ Spotify client working for user: {user_info.get('display_name')}"
            )
        except Exception as e:
            logger.error(f"❌ Spotify client test failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spotify authentication failed",
            )

        # Generate thread_id if not provided
        thread_id = chat_request.thread_id or str(uuid.uuid4())
        logger.info(f"🧵 Using thread ID: {thread_id}")

        # Prepare the state for the agent
        initial_state = {
            "messages": [HumanMessage(content=chat_request.message)],
            "playlist_id": None,
            "playlist_name": None,
            "user_intent": chat_request.message,
        }
        logger.debug(f"📋 Initial state prepared: {initial_state}")

        # Configuration for the agent
        config = {
            "configurable": {
                "thread_id": thread_id,
                "spotify_client": spotify_client,
            }
        }
        logger.debug(f"⚙️  Agent config prepared")

        # Call the LangGraph agent
        logger.info(
            f"🤖 Calling LangGraph agent with message: '{chat_request.message[:100]}{'...' if len(chat_request.message) > 100 else ''}'"
        )

        try:
            result = await assistant_ui_graph.ainvoke(initial_state, config)
            logger.info(f"✅ Agent completed successfully")
            logger.debug(f"📤 Agent result: {result}")
        except Exception as agent_error:
            logger.error(f"💥 Agent execution failed: {agent_error}")
            logger.error(f"Agent error type: {type(agent_error).__name__}")
            logger.error(f"Agent error details: {str(agent_error)}", exc_info=True)
            raise

        # Extract the final message
        if result and result.get("messages"):
            final_message = result["messages"][-1]
            response_content = (
                final_message.content
                if hasattr(final_message, "content")
                else str(final_message)
            )
            logger.debug(
                f"📝 Final message content: {response_content[:200]}{'...' if len(str(response_content)) > 200 else ''}"
            )
        else:
            logger.warning("⚠️  No messages in result, using fallback response")
            response_content = "I apologize, but I encountered an issue processing your request. Please try again."

        # Extract playlist data if available
        playlist_data = result.get("playlist_data") if result else None
        if playlist_data:
            # Ensure data consistency before creating PlaylistData model
            tracks = playlist_data.get('tracks', [])
            if not isinstance(tracks, list):
                tracks = []
                playlist_data['tracks'] = tracks
            
            # Ensure all required fields are present with proper types
            playlist_data.setdefault('total_tracks', len(tracks))
            playlist_data['owner'] = playlist_data.get('owner') or 'Unknown'
            playlist_data.setdefault('images', [])
            
            track_count = len(tracks)
            logger.debug(
                f"🎵 Playlist data found in result: {playlist_data.get('name', 'Unknown')} with {track_count} tracks"
            )

        # Log final state for debugging
        logger.debug(f"📊 Final agent state: user_intent='{result.get('user_intent')}', playlist_id={result.get('playlist_id')}, playlist_name='{result.get('playlist_name')}'")
        
        logger.info(f"✅ Chat processing completed successfully for thread {thread_id}")

        return ChatResponse(
            message=response_content,
            thread_id=thread_id,
            playlist_data=PlaylistData(**playlist_data) if playlist_data else None,
        )

    except HTTPException as http_error:
        logger.error(f"🔴 HTTP Error: {http_error.status_code} - {http_error.detail}")
        raise
    except Exception as e:
        logger.error(f"💥 Unexpected error in chat endpoint: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
