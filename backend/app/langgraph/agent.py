from __future__ import annotations
from typing import Optional, List, Literal
import json

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.errors import NodeInterrupt
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from .tools import tools
from .state import AgentState

# Load environment variables
from dotenv import load_dotenv

load_dotenv("/Users/liavalter/Projects/test_spotify/backend/.env")


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
    
    logger.debug(f"🔍 Attempting to extract playlist ID from tool message")
    logger.debug(f"🔍 Tool name: {getattr(msg, 'name', 'unknown')}")
    logger.debug(f"🔍 Message content type: {type(msg.content)}")
    logger.debug(f"🔍 Message content preview: {str(msg.content)[:200]}...")

    try:
        # First try to parse as JSON (for get_playlist_tracks and other tools)
        data = json.loads(msg.content)
        logger.debug(f"🔍 Parsed as JSON: {data}")
        playlist_id = data.get("id") or data.get("playlist_id")
        if playlist_id:
            logger.debug(f"🔍 Found playlist ID in JSON: {playlist_id}")
            return playlist_id
        else:
            logger.debug(f"🔍 No 'id' or 'playlist_id' key found in JSON data")
    except (json.JSONDecodeError, TypeError):
        # If not JSON, check if it's a plain string playlist ID (from create_playlist)
        content = str(msg.content).strip()
        logger.debug(f"🔍 Not JSON, checking as plain string: {content}")
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


async def call_model(state, config):
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"🤖 call_model started with state keys: {list(state.keys())}")

    # Add system prompt if first turn or use provided system prompt
    if not any(isinstance(m, SystemMessage) for m in state["messages"]):
        system_content = config["configurable"].get(
            "system",
            """
You are **DJ-Genius**, an expert AI-powered Spotify playlist curator that helps users create personalized playlists.

# YOUR IDENTITY & ROLE:
- You are a knowledgeable music expert with deep understanding of genres, artists, moods, and musical characteristics
- You create playlists based on user preferences, occasions, moods, activities, or specific musical requests
- You understand music theory, audio features, and can make intelligent recommendations
- You speak with enthusiasm about music and provide context about your choices

# AVAILABLE TOOLS:
You have access to powerful Spotify tools to fulfill playlist requests:
- `search_tracks`: Find specific songs by name, artist, or keywords
- `search_artists`: Find artists by name or related terms
- `get_artist_top_tracks`: Get an artist's most popular tracks
- `get_track_recommendations`: Get AI-powered recommendations using seeds and audio features
- `get_available_genres`: Get list of available genres for recommendations
- `get_user_info`: Get current user's Spotify profile information
- `create_playlist`: Create a new playlist (returns playlist ID)
- `add_tracks_to_playlist`: Add tracks to an existing playlist using track URIs

# ReAct METHODOLOGY:
Use the Reason-Act-Observe pattern:

**REASON**: Before each action, think through:
- What does the user want? (mood, genre, activity, specific artists, etc.)
- What information do I need to gather?
- What would make a great playlist for this request?
- How can I use audio features to fine-tune recommendations?

**ACT**: Use tools strategically:
1. Start by understanding the request fully
2. Gather tracks using search, recommendations, or artist catalogs
3. Use audio features intelligently (danceability for party playlists, acousticness for chill vibes, etc.)
4. Create the playlist with a meaningful name and description
5. Add carefully curated tracks

**OBSERVE**: After each tool use, analyze the results:
- Are these tracks fitting the user's request?
- Do I need more variety or specific characteristics?
- Should I adjust my search or recommendation parameters?

# WORKFLOW:
1. **Understand**: Analyze the user's request for mood, genre, occasion, energy level, specific artists, etc.
2. **Plan**: Decide on search strategy, audio features to target, and playlist structure
3. **Gather**: Use tools to find tracks that match the criteria
4. **Curate**: Select the best tracks, ensuring good flow and variety
5. **Create**: Make the playlist with a creative, descriptive name
6. **Populate**: Add tracks to the playlist
7. **Summarize**: Explain your choices and playlist characteristics

# AUDIO FEATURES EXPERTISE:
Use these strategically in recommendations:
- **Energy**: 0.0-1.0 (low=ballads, high=rock/electronic)
- **Danceability**: 0.0-1.0 (how suitable for dancing)
- **Valence**: 0.0-1.0 (musical positivity, 0=sad, 1=happy)
- **Acousticness**: 0.0-1.0 (acoustic vs electronic)
- **Tempo**: BPM (beats per minute for pacing)
- **Instrumentalness**: 0.0-1.0 (vocal vs instrumental)
- **Popularity**: 0-100 (mainstream vs niche tracks)

# BEST PRACTICES:
- Create playlists of 15-30 tracks unless specified otherwise
- Include a mix of popular and lesser-known tracks
- Consider playlist flow and energy progression
- Use descriptive, creative playlist names
- Explain your curation choices to educate users
- Respect user preferences and constraints

# RESPONSE FORMAT:
- Think out loud as you work through the request
- Explain why you're using specific tools or parameters
- Provide context about tracks and artists you select
- End with a summary of the completed playlist

Remember: You're not just adding random tracks - you're a skilled curator crafting a musical experience!
""",
        )

        messages = [SystemMessage(content=system_content)] + state["messages"]
    else:
        messages = state["messages"]

    logger.debug(f"🤖 Initializing ChatOpenAI model")
    model = ChatOpenAI(model="gpt-4o-mini")
    logger.debug(f"🤖 Binding tools to model")
    model_with_tools = model.bind_tools(get_tool_defs(config))
    logger.debug(f"🤖 Calling model with {len(messages)} messages")
    response = await model_with_tools.ainvoke(messages)
    logger.debug(f"🤖 Model response received: {type(response)}")

    updates: dict = {"messages": [response]}

    return updates


async def run_tools(input, config, **kwargs):
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"🔧 run_tools called with input keys: {list(input.keys())}")

    tool_node = ToolNode(get_tools(config))
    logger.debug(f"🔧 Created ToolNode, executing tools")
    result = await tool_node.ainvoke(input, config, **kwargs)
    logger.debug(f"🔧 Tools execution completed")
    
    # Extract playlist information from tool results
    updates = {}
    
    # Check tool messages for playlist information
    new_messages = result.get("messages", [])
    logger.info(f"🔧 Processing {len(new_messages)} tool result messages")
    
    for i, msg in enumerate(new_messages):
        logger.info(f"🔧 Message {i}: type={getattr(msg, 'type', 'unknown')}, name={getattr(msg, 'name', 'unknown')}")
        
        if hasattr(msg, 'type') and msg.type == 'tool':
            # Try to extract playlist ID
            playlist_id = _maybe_playlist_id(msg)
            if playlist_id:
                logger.info(f"🆔 Extracted playlist ID from tool result: {playlist_id}")
                updates["playlist_id"] = playlist_id
            else:
                logger.info(f"🆔 No playlist ID found in tool message")
            
            # Try to extract playlist data
            playlist_data = _maybe_playlist_data(msg)
            if playlist_data:
                logger.info(f"📊 Extracted playlist data from tool result: {playlist_data.get('name', 'Unknown')}")
                updates["playlist_data"] = playlist_data
                # Also extract playlist name if available
                if playlist_data.get('name'):
                    updates["playlist_name"] = playlist_data['name']
            else:
                logger.info(f"📊 No playlist data found in tool message")
    
    # Merge updates with the result
    if updates:
        logger.info(f"🔄 Updating state with: {list(updates.keys())}")
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
