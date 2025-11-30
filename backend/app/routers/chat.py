"""
Chat router for LangGraph agent integration
"""

import uuid
import logging
import spotipy
import os
import json
import asyncio
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from ..api.models import ChatRequest, ChatResponse, PlaylistData
from ..services.spotify_service import spotify_service
from ..langgraph_agent.agent import assistant_ui_graph
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest, request: Request):
    """Chat endpoint that integrates with LangGraph agent using service account"""

    logger.info("🚀 Chat request received (no authentication required)")
    logger.debug(f"📝 Message: {chat_request.message}")
    logger.debug(f"🔗 Thread ID: {chat_request.thread_id}")

    spotify_client = await spotify_service.get_client()

    try:
        # Generate thread_id if not provided
        thread_id = chat_request.thread_id or str(uuid.uuid4())
        logger.info(f"🧵 Using thread ID: {thread_id}")

        ultrathink_enabled = bool(chat_request.ultrathink)
        selected_model = settings.openrouter_model
        if ultrathink_enabled and settings.ultrathink_openrouter_model:
            selected_model = settings.ultrathink_openrouter_model
        elif ultrathink_enabled:
            logger.warning(
                "⚠️ ULTRATHINK requested but ULTRATHINK_OPENROUTER_MODEL is not configured. Falling back to OPENROUTER_MODEL."
            )

            # Prepare the state for the agent
            # Note: Do NOT set playlist_id/playlist_name to None here - let the checkpointer
            # preserve these values across conversation turns for playlist continuity
            initial_state = {
                "messages": [HumanMessage(content=chat_request.message)],
                "user_intent": chat_request.message,
            }
        logger.debug(f"📋 Initial state prepared: {initial_state}")

        # Configuration for the agent
        config = {
            "configurable": {
                "thread_id": thread_id,
                "spotify_client": spotify_client,
                "openrouter_model_override": selected_model,
            },
            "recursion_limit": 100,
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
            tracks = playlist_data.get("tracks", [])
            if not isinstance(tracks, list):
                tracks = []
                playlist_data["tracks"] = tracks

            # Ensure all required fields are present with proper types
            playlist_data.setdefault("total_tracks", len(tracks))
            playlist_data["owner"] = playlist_data.get("owner") or "Unknown"
            playlist_data.setdefault("images", [])
            playlist_data.setdefault("external_urls", {})

            track_count = len(tracks)
            logger.debug(
                f"🎵 Playlist data found in result: {playlist_data.get('name', 'Unknown')} with {track_count} tracks"
            )

        # Log final state for debugging
        logger.debug(
            f"📊 Final agent state: user_intent='{result.get('user_intent')}', playlist_id={result.get('playlist_id')}, playlist_name='{result.get('playlist_name')}'"
        )

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


@router.post("/chat/stream")
async def chat_stream_endpoint(chat_request: ChatRequest, request: Request):
    """Streaming chat endpoint that sends tool call updates via Server-Sent Events"""

    logger.info("🚀 Streaming chat request received")
    logger.debug(f"📝 Message: {chat_request.message}")
    logger.debug(f"🔗 Thread ID: {chat_request.thread_id}")

    async def event_generator():
        try:
            spotify_client = await spotify_service.get_client()

            # Generate thread_id if not provided
            thread_id = chat_request.thread_id or str(uuid.uuid4())
            logger.info(f"🧵 Using thread ID: {thread_id}")

            ultrathink_enabled = bool(chat_request.ultrathink)
            selected_model = settings.openrouter_model
            if ultrathink_enabled and settings.ultrathink_openrouter_model:
                selected_model = settings.ultrathink_openrouter_model
            elif ultrathink_enabled:
                logger.warning(
                    "⚠️ ULTRATHINK requested but ULTRATHINK_OPENROUTER_MODEL is not configured. Falling back to OPENROUTER_MODEL."
                )

            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting...'})}\n\n"

            # Prepare the state for the agent
            # Note: Do NOT set playlist_id/playlist_name to None here - let the checkpointer
            # preserve these values across conversation turns for playlist continuity
            initial_state = {
                "messages": [HumanMessage(content=chat_request.message)],
                "user_intent": chat_request.message,
            }

            # Configuration for the agent
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "spotify_client": spotify_client,
                    "openrouter_model_override": selected_model,
                },
                "recursion_limit": 100,
            }

            # Call the LangGraph agent with streaming
            logger.info(f"🤖 Calling LangGraph agent in streaming mode")

            # Stream through agent execution and build up the final state
            # Use a smarter merge that preserves important data like playlist_data
            final_state = {"messages": []}
            async for event in assistant_ui_graph.astream(initial_state, config):
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("Client disconnected")
                    break

                # Process agent events and accumulate state
                if "agent" in event:
                    agent_output = event["agent"]
                    # Smart merge: append messages, preserve playlist data
                    if "messages" in agent_output:
                        final_state["messages"].extend(agent_output["messages"])
                    # Preserve playlist_data once it's set (don't overwrite with None)
                    for key in ["playlist_data", "playlist_id", "playlist_name"]:
                        if agent_output.get(key) is not None:
                            final_state[key] = agent_output[key]
                    # Copy other non-critical fields
                    for key in agent_output:
                        if key not in [
                            "messages",
                            "playlist_data",
                            "playlist_id",
                            "playlist_name",
                        ]:
                            final_state[key] = agent_output[key]

                    messages = agent_output.get("messages", [])
                    if messages:
                        last_message = messages[-1]
                        # Check for tool calls
                        if (
                            hasattr(last_message, "tool_calls")
                            and last_message.tool_calls
                        ):
                            for tool_call in last_message.tool_calls:
                                tool_name = tool_call.get("name")
                                # Map tool names to friendly messages
                                tool_messages = {
                                    "search_tracks": "🔍 Searching for tracks...",
                                    "search_artists": "👤 Searching for artists...",
                                    "get_artist_top_tracks": "🎵 Getting artist's top tracks...",
                                    "get_track_recommendations": "✨ Getting personalized recommendations...",
                                    "get_available_genres": "🎼 Fetching available genres...",
                                    "create_playlist": "📝 Creating your playlist...",
                                    "create_and_populate_playlist": "🎵 Creating and populating your playlist...",
                                    "add_tracks_to_playlist": "➕ Adding tracks to playlist...",
                                    "get_playlist_tracks": "📋 Getting playlist tracks...",
                                    "tavily_search": "🌐 Researching music context (Powered by Tavily)...",
                                    "get_user_info": "👤 Getting user information...",
                                    "get_audio_features": "🎚️ Analyzing audio features...",
                                    "remove_tracks_from_playlist": "➖ Removing tracks from playlist...",
                                }

                                friendly_message = tool_messages.get(
                                    tool_name, f"⚙️ Running {tool_name}"
                                )

                                yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'message': friendly_message})}\n\n"
                                await asyncio.sleep(0)  # Yield control

                elif "tools" in event:
                    # Tool execution completed - smart merge tools output
                    tools_output = event["tools"]
                    if "messages" in tools_output:
                        final_state["messages"].extend(tools_output["messages"])
                    # Preserve playlist_data once it's set (don't overwrite with None)
                    for key in ["playlist_data", "playlist_id", "playlist_name"]:
                        if tools_output.get(key) is not None:
                            final_state[key] = tools_output[key]
                            logger.info(
                                f"🎵 Captured {key} from tools: {tools_output[key] if key != 'playlist_data' else tools_output[key].get('name', 'Unknown')}"
                            )
                    # Copy other fields
                    for key in tools_output:
                        if key not in [
                            "messages",
                            "playlist_data",
                            "playlist_id",
                            "playlist_name",
                        ]:
                            final_state[key] = tools_output[key]

                    yield f"data: {json.dumps({'type': 'tool_end'})}\n\n"
                    await asyncio.sleep(0)

            # Use the accumulated final state
            result = (
                final_state if final_state and final_state.get("messages") else None
            )

            # Log what we captured
            if result:
                logger.info(
                    f"📊 Streaming completed - messages: {len(result.get('messages', []))}, playlist_data: {'yes' if result.get('playlist_data') else 'no'}"
                )

            # If we didn't get a result from streaming, fall back to invoke
            if result is None or not result.get("messages"):
                logger.warning("⚠️ No result from streaming, falling back to ainvoke")
                result = await assistant_ui_graph.ainvoke(initial_state, config)
                logger.info(
                    f"📊 Fallback invoke - playlist_data: {'yes' if result.get('playlist_data') else 'no'}"
                )

            # Extract the final message
            response_content = (
                "I apologize, but I encountered an issue processing your request."
            )
            if result and result.get("messages"):
                final_message = result["messages"][-1]
                response_content = (
                    final_message.content
                    if hasattr(final_message, "content")
                    else str(final_message)
                )

            # Extract playlist data if available
            playlist_data = result.get("playlist_data") if result else None
            if playlist_data:
                tracks = playlist_data.get("tracks", [])
                if not isinstance(tracks, list):
                    tracks = []
                    playlist_data["tracks"] = tracks

                playlist_data.setdefault("total_tracks", len(tracks))
                playlist_data["owner"] = playlist_data.get("owner") or "Unknown"
                playlist_data.setdefault("images", [])
                playlist_data.setdefault("external_urls", {})

            # Send final response
            final_response = {
                "type": "complete",
                "message": response_content,
                "thread_id": thread_id,
                "playlist_data": playlist_data,
            }

            yield f"data: {json.dumps(final_response)}\n\n"
            logger.info(
                f"✅ Streaming chat completed successfully for thread {thread_id}"
            )

        except Exception as e:
            logger.error(f"💥 Streaming error: {str(e)}", exc_info=True)
            error_response = {
                "type": "error",
                "message": f"Chat processing failed: {str(e)}",
            }
            yield f"data: {json.dumps(error_response)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
