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
from langmem.short_term import summarize_messages, RunningSummary

# Summarization constants
SUMMARIZATION_MAX_TOKENS = 10000  # Maximum tokens in final output after summarization
SUMMARIZATION_TRIGGER_TOKENS = 10000  # Token threshold to trigger summarization
SUMMARIZATION_MAX_SUMMARY_TOKENS = 256  # Maximum tokens for the summary itself

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
    """Extract playlist data from tool message if it's a valid playlist result"""
    import logging

    logger = logging.getLogger(__name__)

    try:
        data = json.loads(msg.content)
        # Check if this looks like playlist data (has tracks, name, etc.)
        # Also make sure it's not an error response
        if (
            isinstance(data, dict)
            and "tracks" in data
            and "name" in data
            and "error" not in data
        ):
            logger.debug(
                f"🎵 Valid playlist data found: {data.get('name')} with {len(data.get('tracks', []))} tracks"
            )
            return data
        elif isinstance(data, dict) and "error" in data:
            logger.warning(f"⚠️ Tool returned error: {data.get('error')}")
        return None
    except Exception as e:
        logger.debug(f"Could not parse playlist data: {e}")
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
        messages = list(state["messages"])

    logger.debug("🤖 Initializing ChatOpenAI model for OpenRouter")
    headers = {}
    if settings.openrouter_referer:
        headers["HTTP-Referer"] = settings.openrouter_referer
    if settings.openrouter_title:
        headers["X-Title"] = settings.openrouter_title

    configurable = config.get("configurable", {})
    # Always use standard openrouter_model for summarization (not ultrathink)
    model_name = configurable.get(
        "openrouter_model_override", settings.openrouter_model
    )

    logger.debug(f"🤖 Using OpenRouter model: {model_name}")

    model_config = {
        "api_key": settings.openrouter_api_key,
        "base_url": settings.openrouter_base_url,
        "model": model_name,
        "default_headers": headers or None,
    }

    # Apply low reasoning effort specifically for openai/gpt-5
    if model_name and model_name.lower().startswith("openai/gpt-5"):
        logger.debug("🤖 Applying low reasoning effort for openai/gpt-5")
        model_config["reasoning_effort"] = "low"

    model = ChatOpenAI(**model_config)

    # Apply langmem summarization when messages exceed 10k tokens
    running_summary = (
        state.get("context", {}).get("running_summary")
        if state.get("context")
        else None
    )

    # Create summarization model using standard openrouter_model (not ultrathink)
    summarization_model_config = {
        "api_key": settings.openrouter_api_key,
        "base_url": settings.openrouter_base_url,
        "model": settings.openrouter_model,  # Always use standard model for summarization
        "default_headers": headers or None,
    }
    summarization_model = ChatOpenAI(**summarization_model_config)

    summarization_result = summarize_messages(
        messages,
        running_summary=running_summary,
        model=summarization_model,
        max_tokens=SUMMARIZATION_MAX_TOKENS,
        max_tokens_before_summary=SUMMARIZATION_TRIGGER_TOKENS,
        max_summary_tokens=SUMMARIZATION_MAX_SUMMARY_TOKENS,
    )

    # Use summarized messages for LLM call
    messages_for_llm = summarization_result.messages
    logger.debug(
        f"📝 After summarization: {len(messages)} -> {len(messages_for_llm)} messages"
    )

    logger.debug(f"🤖 Binding tools to model")
    model_with_tools = model.bind_tools(get_tool_defs(config))
    logger.debug(f"🤖 Calling model with {len(messages_for_llm)} messages")
    response = await model_with_tools.ainvoke(messages_for_llm)
    logger.debug(f"🤖 Model response received: {type(response)}")

    updates: dict = {"messages": [response]}

    # Update context with running summary if summarization occurred
    if summarization_result.running_summary:
        updates["context"] = {"running_summary": summarization_result.running_summary}
        logger.info("📝 Updated running summary in context")

    return updates


@traceable(name="spotify_dj_agent_run_tools")
async def run_tools(input, config, **kwargs):
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"🔧 run_tools called with input keys: {list(input.keys())}")

    # Initialize caches in config from state (tools read from these)
    configurable = config.setdefault("configurable", {})
    configurable.setdefault("search_cache", input.get("search_cache", {}))
    configurable.setdefault("track_cache", input.get("track_cache", {}))
    configurable.setdefault("artist_cache", input.get("artist_cache", {}))

    # Execute tools
    tool_node = ToolNode(get_tools(config))
    logger.debug("🔧 Executing tools")
    result = await tool_node.ainvoke(input, config, **kwargs)
    logger.debug("🔧 Tools execution completed")

    # Extract playlist information from ALL tool results (supports parallel tool calls)
    updates = {}
    for msg in result.get("messages", []):
        if not hasattr(msg, "content"):
            continue

        # Check for playlist ID
        playlist_id = _maybe_playlist_id(msg)
        if playlist_id and "playlist_id" not in updates:
            logger.info(f"🎵 Extracted playlist_id: {playlist_id}")
            updates["playlist_id"] = playlist_id

        # Check for playlist data (from create_and_populate_playlist or get_playlist_tracks)
        playlist_data = _maybe_playlist_data(msg)
        if playlist_data and "playlist_data" not in updates:
            logger.info(
                f"🎵 Extracted playlist_data: {playlist_data.get('name', 'Unknown')}"
            )
            updates["playlist_data"] = playlist_data
            if playlist_data.get("name"):
                updates["playlist_name"] = playlist_data["name"]

    # Persist caches back to state
    updates["search_cache"] = configurable.get("search_cache", {})
    updates["track_cache"] = configurable.get("track_cache", {})
    updates["artist_cache"] = configurable.get("artist_cache", {})

    result.update(updates)
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
