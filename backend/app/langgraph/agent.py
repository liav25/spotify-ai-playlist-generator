from __future__ import annotations
from typing import Optional
import json
import os

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.errors import NodeInterrupt
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from .tools import tools
from .state import AgentState
from .prompts import build_system_prompt
from ..core.config import settings

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Import and configure LangSmith tracing
try:
    from langsmith import traceable
    from langsmith import Client as LangSmithClient

    # Initialize LangSmith client if API key is available
    langsmith_client = None
    if (
        os.getenv("LANGSMITH_API_KEY")
        and os.getenv("LANGSMITH_TRACING_ENABLED", "true").lower() == "true"
    ):
        langsmith_client = LangSmithClient(
            api_key=os.getenv("LANGSMITH_API_KEY"),
            api_url=os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com"),
        )
        # Set environment variables for automatic tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = os.getenv(
            "LANGSMITH_PROJECT", "spotify-ai-playlist-generator"
        )
        print("✅ LangSmith tracing initialized")
    else:
        print("ℹ️  LangSmith tracing disabled - no API key provided")

except ImportError:
    print("⚠️  LangSmith not available - install langsmith package for tracing")
    traceable = lambda func: func  # No-op decorator
    langsmith_client = None


class AnyArgsSchema(BaseModel):
    class Config:
        extra = "allow"


class FrontendTool(BaseTool):
    def __init__(self, name: str):
        super().__init__(name=name, description="", args_schema=AnyArgsSchema)

    def _run(self, *args, **kwargs):
        raise NodeInterrupt("This is a frontend tool call")

    async def _arun(self, *args, **kwargs) -> str:
        raise NodeInterrupt("This is a frontend tool call")


def get_tool_defs(config):
    frontend_tools = [
        {"type": "function", "function": tool}
        for tool in config["configurable"].get("frontend_tools", [])
    ]
    return tools + frontend_tools


def get_tools(config):
    frontend_tools = [
        FrontendTool(tool.name)
        for tool in config["configurable"].get("frontend_tools", [])
    ]
    return tools + frontend_tools


def _maybe_playlist_id(msg: ToolMessage) -> Optional[str]:
    import logging

    logger = logging.getLogger(__name__)

    try:
        # First try to parse as JSON (for create_playlist, get_playlist_tracks and other tools)
        data = json.loads(msg.content)
        playlist_id = data.get("id") or data.get("playlist_id")
        if playlist_id:
            logger.debug(f"🔍 Found playlist ID in JSON: {playlist_id}")
            return playlist_id
    except (json.JSONDecodeError, TypeError):
        # If not JSON, check if it's a plain string playlist ID
        content = str(msg.content).strip()
        # Spotify playlist IDs are typically 22 characters long, alphanumeric
        if (
            content
            and len(content) >= 15
            and content.replace("_", "").replace("-", "").isalnum()
        ):
            logger.debug(f"🔍 Found playlist ID as string: {content}")
            return content
        logger.debug(f"🔍 Content not recognized as playlist ID: {content[:50]}...")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Error extracting playlist ID: {e}")
        return None


def _maybe_playlist_data(msg: ToolMessage) -> Optional[dict]:
    """Extract playlist data from tool message if it's a get_playlist_tracks result"""
    try:
        data = json.loads(msg.content)
        # Check if this looks like playlist data (has tracks, name, etc.)
        if isinstance(data, dict) and "tracks" in data and "name" in data:
            return data
        return None
    except Exception:
        return None


@traceable(name="spotify_dj_agent_call_model")
async def call_model(state, config):
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"🤖 call_model started with state keys: {list(state.keys())}")

    # Add tracing metadata (if LangSmith is available)
    if langsmith_client:
        # Metadata for tracing context
        pass

    # Add system prompt if first turn or use provided system prompt
    if not any(isinstance(m, SystemMessage) for m in state["messages"]):
        system_content = config["configurable"].get(
            "system",
            build_system_prompt(),
        )

        messages = [SystemMessage(content=system_content)] + state["messages"]
    else:
        messages = state["messages"]

    logger.debug(f"🤖 Initializing ChatOpenAI model")
    model = ChatOpenAI(model=settings.openai_model, reasoning_effort="low")
    logger.debug(f"🤖 Binding tools to model")
    model_with_tools = model.bind_tools(get_tool_defs(config))
    logger.debug(f"🤖 Calling model with {len(messages)} messages")
    response = await model_with_tools.ainvoke(messages)
    logger.debug(f"🤖 Model response received: {type(response)}")

    updates: dict = {"messages": [response]}

    return updates


@traceable(name="spotify_dj_agent_run_tools")
async def run_tools(input, config, **kwargs):
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"🔧 run_tools called with input keys: {list(input.keys())}")

    # Initialize caches in config if not present
    if "search_cache" not in config.get("configurable", {}):
        config.setdefault("configurable", {})["search_cache"] = input.get(
            "search_cache", {}
        )
    if "track_cache" not in config.get("configurable", {}):
        config["configurable"]["track_cache"] = input.get("track_cache", {})
    if "artist_cache" not in config.get("configurable", {}):
        config["configurable"]["artist_cache"] = input.get("artist_cache", {})

    # Extract tool information for tracing
    tool_calls = []
    if input.get("messages") and len(input["messages"]) > 0:
        last_message = input["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_calls = [
                {"name": tool_call["name"], "args": tool_call.get("args", {})}
                for tool_call in last_message.tool_calls
            ]

    if langsmith_client and tool_calls:
        # Metadata for tracing context
        pass

    tool_node = ToolNode(get_tools(config))
    logger.debug(f"🔧 Created ToolNode, executing tools")
    result = await tool_node.ainvoke(input, config, **kwargs)
    logger.debug(f"🔧 Tools execution completed")

    # Extract playlist information from tool results and update state
    updates = {}

    # Check the last message for tool results
    if result.get("messages") and len(result["messages"]) > 0:
        last_message = result["messages"][-1]
        if hasattr(last_message, "content"):
            # Check for playlist ID
            playlist_id = _maybe_playlist_id(last_message)
            if playlist_id:
                logger.info(f"🎵 Extracted playlist_id from tool result: {playlist_id}")
                updates["playlist_id"] = playlist_id

            # Check for playlist data
            playlist_data = _maybe_playlist_data(last_message)
            if playlist_data:
                logger.info(
                    f"🎵 Extracted playlist_data from tool result: {playlist_data.get('name', 'Unknown')}"
                )
                updates["playlist_data"] = playlist_data
                # Also extract playlist name if not already set
                if playlist_data.get("name") and not input.get("playlist_name"):
                    updates["playlist_name"] = playlist_data["name"]
                    logger.info(f"🎵 Extracted playlist_name: {playlist_data['name']}")

    # Update caches from tool execution
    # Populate cache from tool calls if they were executed
    if tool_calls:
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            args = tool_call.get("args", {})

            # Cache tavily_search results
            if tool_name == "tavily_search" and result.get("messages"):
                query = args.get("query")
                if query:
                    # Find the tool message response
                    for msg in reversed(result["messages"]):
                        if hasattr(msg, "content") and isinstance(msg.content, str):
                            if not config["configurable"]["search_cache"].get(query):
                                config["configurable"]["search_cache"][
                                    query
                                ] = msg.content
                                logger.info(
                                    f"💾 Cached Tavily search result for: '{query}'"
                                )
                            break

            # Cache search_tracks results
            elif tool_name == "search_tracks" and result.get("messages"):
                query = args.get("query")
                limit = args.get("limit", 20)
                market = args.get("market", "US")
                cache_key = f"{query}_{limit}_{market}"
                if query:
                    for msg in reversed(result["messages"]):
                        if hasattr(msg, "content"):
                            try:
                                content = (
                                    json.loads(msg.content)
                                    if isinstance(msg.content, str)
                                    else msg.content
                                )
                                if isinstance(content, list) and len(content) > 0:
                                    if not config["configurable"]["track_cache"].get(
                                        cache_key
                                    ):
                                        config["configurable"]["track_cache"][
                                            cache_key
                                        ] = content
                                        logger.info(
                                            f"💾 Cached track search result for: '{query}'"
                                        )
                                    break
                            except:
                                pass

            # Cache search_artists results
            elif tool_name == "search_artists" and result.get("messages"):
                query = args.get("query")
                limit = args.get("limit", 10)
                cache_key = f"{query}_{limit}"
                if query:
                    for msg in reversed(result["messages"]):
                        if hasattr(msg, "content"):
                            try:
                                content = (
                                    json.loads(msg.content)
                                    if isinstance(msg.content, str)
                                    else msg.content
                                )
                                if isinstance(content, list) and len(content) > 0:
                                    if not config["configurable"]["artist_cache"].get(
                                        cache_key
                                    ):
                                        config["configurable"]["artist_cache"][
                                            cache_key
                                        ] = content
                                        logger.info(
                                            f"💾 Cached artist search result for: '{query}'"
                                        )
                                    break
                            except:
                                pass

    # Persist caches back to state
    updates["search_cache"] = config["configurable"].get("search_cache", {})
    updates["track_cache"] = config["configurable"].get("track_cache", {})
    updates["artist_cache"] = config["configurable"].get("artist_cache", {})

    # Merge updates with result
    if updates:
        result.update(updates)
        logger.debug(f"🎵 Updated state with: {list(updates.keys())}")

    return result


def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return END
    else:
        return "tools"


# Define the graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", run_tools)

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    ["tools", END],
)

workflow.add_edge("tools", "agent")

assistant_ui_graph = workflow.compile(checkpointer=InMemorySaver())
