"""
Chat router for LangGraph agent integration
"""

import uuid
import logging
import spotipy
from fastapi import APIRouter, HTTPException, status, Request
from langchain_core.messages import HumanMessage

from ..api.models import ChatRequest, ChatResponse, PlaylistData
from ..services.auth_service import get_current_user_from_header
from ..services.user_service import user_sessions
from ..langgraph.agent import assistant_ui_graph

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
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