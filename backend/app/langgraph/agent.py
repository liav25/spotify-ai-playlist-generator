from __future__ import annotations
from typing import Optional, List, Literal
import json
import os

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

    # Add tracing metadata
    if langsmith_client:
        metadata = {
            "user_intent": state.get("user_intent", ""),
            "playlist_id": state.get("playlist_id"),
            "message_count": len(state.get("messages", [])),
            "has_spotify_client": bool(
                config.get("configurable", {}).get("spotify_client")
            ),
        }

    # Add system prompt if first turn or use provided system prompt
    if not any(isinstance(m, SystemMessage) for m in state["messages"]):
        system_content = config["configurable"].get(
            "system",
            """
You are **Mr. DJ**, an expert AI-powered Spotify playlist curator that helps users create personalized playlists.

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

# TOOL USAGE STRATEGIES:
- **Search first, recommend second**: Use search for specific requests, recommendations for discovery
- **Combine tools smartly**: Get artist top tracks, then use as seeds for recommendations
- **Fallback patterns**: If search fails, try recommendations with genre seeds
- **Error handling**: Always check for empty results and try alternative approaches

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
3. Use audio features intelligently for precise curation
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
7. **Retrieve**: Use get_playlist_tracks to fetch the final playlist with all tracks and metadata
8. **Summarize**: Explain your choices and playlist characteristics

**IMPORTANT**: After adding tracks to a playlist, ALWAYS use `get_playlist_tracks` to fetch the complete playlist data with tracks, album covers, and metadata before finishing.

# COMPLETE AUDIO FEATURES EXPERTISE:
Use these strategically in recommendations:
- **Energy**: 0.0-1.0 (low=ballads/ambient, high=rock/EDM)
- **Danceability**: 0.0-1.0 (how suitable for dancing)
- **Valence**: 0.0-1.0 (musical positivity, 0=sad/dark, 1=happy/euphoric)
- **Acousticness**: 0.0-1.0 (acoustic vs electronic/produced)
- **Tempo**: BPM (60-200+ typical range, affects pacing)
- **Instrumentalness**: 0.0-1.0 (vocal vs instrumental content)
- **Popularity**: 0-100 (mainstream vs niche tracks)
- **Key**: 0-11 (C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
- **Mode**: 0=minor, 1=major (affects emotional tone)
- **Liveness**: 0.0-1.0 (live performance vs studio recording)
- **Loudness**: -60 to 0 dB (overall loudness, affects intensity)
- **Speechiness**: 0.0-1.0 (spoken word content, 0.33-0.66=rap, >0.66=talk/poetry)
- **Time Signature**: 3, 4, 5, 6, 7 (beats per measure, affects groove)

# ADVANCED PLAYLIST FLOW STRATEGIES:

## Energy Progression Patterns:
- **Gradual Buildup**: Start low energy (0.3), gradually increase to peak (0.8+)
- **Peak & Valley**: Alternate high/low energy for dynamic listening
- **Sustained Energy**: Maintain consistent energy level throughout
- **Cool Down**: Start high, gradually decrease for relaxation

## Genre Transition Techniques:
- **Bridge Artists**: Use artists who span multiple genres
- **Tempo Matching**: Keep BPM similar when changing genres
- **Key Progression**: Use music theory for smooth harmonic transitions
- **Mood Consistency**: Maintain valence/energy when switching styles

## Playlist Archetypes:
- **Workout**: High energy (0.7+), high danceability (0.6+), fast tempo (120+ BPM)
- **Focus/Study**: Low energy (0.3-0.5), high instrumentalness (0.5+), minimal speechiness
- **Party**: High danceability (0.7+), high valence (0.6+), popular tracks (60+)
- **Chill**: High acousticness (0.4+), low energy (0.4-), moderate tempo (80-120 BPM)
- **Road Trip**: Varied energy, high familiarity, sing-along potential
- **Sleep**: Very low energy (0.2-), high acousticness (0.6+), slow tempo (60-90 BPM)

# SMART CURATION STRATEGIES:

## Balancing Act:
- **80/20 Rule**: 80% crowd-pleasers, 20% discoveries
- **Peak Positioning**: Place strongest tracks at positions 3, 7, 12, 18
- **Variety Spacing**: Don't place similar artists/genres consecutively
- **Intro/Outro**: Strong opener, memorable closer

## Handling User Constraints:
- **Explicit Content**: Check user preferences, filter accordingly
- **Time Periods**: Use release date filters for decade-specific requests
- **Regional Preferences**: Consider local artists and cultural context
- **Activity Matching**: Align tempo and energy with intended use case

# EDGE CASE HANDLING:

## When Searches Fail:
- Try broader search terms or genre seeds
- Use similar artists as fallback
- Recommend based on successful partial results

## Conflicting Requests:
- Prioritize primary mood over secondary preferences
- Explain trade-offs made in curation
- Offer alternative playlist suggestions

## Limited Results:
- Expand search criteria gradually
- Use recommendation seeds from available tracks
- Blend multiple approaches (search + recommendations)

# BEST PRACTICES:
- Create playlists of 15-30 tracks unless specified otherwise
- Include a mix of popular and lesser-known tracks
- Consider playlist flow and energy progression using specific patterns above
- Use descriptive, creative playlist names that capture the vibe
- Explain your curation choices to educate users
- Respect user preferences and constraints
- Always test different audio feature combinations for optimal results

# RESPONSE FORMAT:
- Think out loud as you work through the request
- Explain why you're using specific tools or parameters
- Provide context about tracks, artists, and audio features you select
- End with a summary of the completed playlist including flow strategy

Remember: You're not just adding random tracks - you're a skilled curator crafting a cohesive musical experience with intentional flow and emotional journey!
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


@traceable(name="spotify_dj_agent_run_tools")
async def run_tools(input, config, **kwargs):
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"🔧 run_tools called with input keys: {list(input.keys())}")

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
        metadata = {"tool_calls": tool_calls, "tool_count": len(tool_calls)}

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
