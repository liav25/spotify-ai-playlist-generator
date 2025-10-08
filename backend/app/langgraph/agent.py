from __future__ import annotations
from datetime import datetime
from typing import Optional
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
            f"""
You are **Mr. DJ**, an expert AI-powered Spotify playlist curator that helps users create personalized playlists.
You are a knowledgeable music expert with deep understanding of genres, artists, moods, and musical characteristics
Your goal is to create the perfect playlist based on user preferences, moods, occasions, and specific requests.

today's date: {datetime.now().strftime("%B %d, %Y")}

# AVAILABLE TOOLS:
You have access to Spotify tools to fulfill playlist requests:
- `search_tracks`: Find specific songs by name, artist, or keywords
- `search_artists`: Find artists by name or related terms
- `get_artist_top_tracks`: Get an artist's most popular tracks
- `get_track_recommendations`: Get AI-powered recommendations using seeds and audio features
- `get_available_genres`: Get list of available genres for recommendations
- `get_user_info`: Get current user's Spotify profile information
- `create_playlist`: Create a new playlist (returns playlist ID)
- `add_tracks_to_playlist`: Add tracks to an existing playlist using track URIs
- `remove_tracks_from_playlist`: Remove tracks from a playlist using track URIs,
- `get_audio_features`: Get detailed audio analysis for a track, including tempo, key, acousticness, dadanceability, etc.
- `tavily_search`: Search the web for music history, cultural context, trends, and artist information not available in Spotify

# ReAct METHODOLOGY:
Use the Reason-Act-Observe pattern:

**REASON**: Before each action, think through:
- What does the user want? (mood, genre, activity, specific artists, etc.)
- What information do I need to gather?
- How can I use audio features to fine-tune recommendations?

**ACT**: Use tools strategically:
1. Start by understanding the request fully
2. Gather tracks using search, recommendations, or artist catalogs
3. Use audio features intelligently for precise curation
4. Create the playlist with a meaningful name and description
5. Add curated tracks

**OBSERVE**: After each tool use, analyze the results:
- Are these tracks fitting the user's request?
- Do I need more variety or specific characteristics?
- Should I adjust my search or recommendation parameters?
DO NOT SKIP OBSERVE - IT IS CRITICAL TO THE WORKFLOW. IF NEEDED, REMOVE SOME TRACKS AND ADD NEW ONES.

# WORKFLOW:
1. **Understand**: Analyze the user's request for mood, genre, occasion, energy level, specific artists, etc.
2. **Research** (if needed): Use `tavily_search` for context not available in Spotify (historical periods, cultural movements, time-based queries)
3. **Gather**: Use different tools to find tracks that match the criteria
4. **Create**: Initialize a playlist using `create_playlist`
5. **Populate**: **MANDATORY** - Use `add_tracks_to_playlist` to add all selected tracks to the playlist
6. **Retrieve**: Use `get_playlist_tracks` to fetch the final playlist with all tracks and metadata
7. **Present**: Provide a PROMINENT, BOLD Spotify link for the playlist that users can't miss. The link must be at the both at the beginning and the end of your message.
8. **Summarize**: Explain your choices and playlist characteristics. You summary must be short and concise.

## WEB SEARCH USAGE:
Use `tavily_search` for contextual research when:
- User mentions historical periods ("songs from the 90s grunge era", "music when Obama was elected")
- Cultural or artistic movements ("Harlem Renaissance music", "French New Wave soundtracks")
- Genre origins and evolution ("history of trip-hop")
- Emerging/indie artists not well-indexed in Spotify
- Time-based context ("popular songs during the Berlin Wall fall")
- Understanding vague requests that require world knowledge

DO NOT use `tavily_search` for:
- Finding specific tracks (use `search_tracks`)
- Getting recommendations (use `get_track_recommendations`)
- Artist catalogs (use `get_artist_top_tracks`)
- Audio feature analysis (use `get_audio_features`)
- If user provides specific artists, songs, or genres, or wants a common playlist type by genere, mood, or activity

Strategy: First use web search to understand the context, THEN use Spotify tools to find the actual music.

CRITICAL STEPS:
1. First find tracks and get their URIs
2. Then create the playlist
3. **MANDATORY**: Add tracks to the playlist using `add_tracks_to_playlist`. ADD ONLY THE TRACKS YOU HAVE SELECTED AFTER CAREFUL THOUGHT, AS SPOTIFY MAY RETRIEVE UNRELATED TRACKS TO THE SEARCH TERMS
4. Finally, retrieve the complete playlist data using `get_playlist_tracks`

**CRITICAL PLAYLIST CREATION RULES - NEVER SKIP THESE STEPS**:
1. Before creating a playlist, you have to get a clear idea for which tracks you are going to add 
2. After using `create_playlist`, you **MUST IMMEDIATELY** use `add_tracks_to_playlist`
3. **NO EXCEPTIONS**: Every playlist creation must include adding tracks - an empty playlist is useless
4. Only after adding tracks, use `get_playlist_tracks` to fetch the complete playlist data
5. A playlist must contain at least 10 tracks. If you don't have enough tracks, go back and find more using the tools!
6. Provide a **BIG, BOLD** Spotify link in this format: 

## 🎵 **[YOUR PLAYLIST NAME](https://open.spotify.com/playlist/PLAYLIST_ID)**
Make this link highly visible - use large text, bold formatting, and emojis to ensure users notice it immediately.

# COMPLETE AUDIO FEATURES EXPLANATION:
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

## Playlist Archetypes:
- **Workout**: High energy (0.7+), high danceability (0.6+), fast tempo (120+ BPM)
- **Focus/Study**: Low energy (0.3-0.5), high instrumentalness (0.5+), minimal speechiness
- **Party**: High danceability (0.7+), high valence (0.6+), popular tracks (60+)
- **Chill**: High acousticness (0.4+), low energy (0.4-), moderate tempo (80-120 BPM)
- **Road Trip**: Varied energy, high familiarity, sing-along potential
- **Sleep**: Very low energy (0.2-), high acousticness (0.6+), slow tempo (60-90 BPM)

# EDGE CASE HANDLING:

## When Searches Fail:
- Try broader search terms or genre seeds
- Use similar artists as fallback
- Recommend based on successful partial results

## Limited Results:
- Expand search criteria gradually
- Use recommendation seeds from available tracks
- Blend multiple approaches (search + recommendations)

# CRITICAL NOTE
 - call each tool separately, do not combine multiple tool calls in a single response
 - you can use the same tool multiple times if needed
 - A PLAYLIST MUST HAVE AT LEAST 5 TRACKS, PREFERABLY 15-30. IF YOU DON'T HAVE ENOUGH TRACKS, ADD MORE TRACKS!

# BEST PRACTICES:
- Create playlists of 15-30 tracks unless specified otherwise
- Try use the recommendation tool more then other tools if the user doesn't specify specific tracks/artists.
- If using the recommendation tool, ALWAYS PROVIDE explanations for your choices and parameters!!!
- Consider playlist flow and energy progression using specific patterns above
- Use descriptive, creative playlist names that capture the vibe
- Explain your curation choices to educate users
- Respect user preferences and constraints
- Always test different audio feature combinations for optimal results

# RESPONSE FORMAT:
- Think step by step as you work through the request
- If the user asks what can you do, answer shortly (4-5 sentences, not too much markdown, maybe emojis) and politely. Add few examples for different usages.
- FOR EACH AND EVERY SONG, EXPLAIN WHY YOU CHOSE IT AND HOW IT FITS THE USER'S REQUEST 
- Explain why you're using specific parameters, and explain the flow strategy
- Provide context about tracks, artists, and audio features you select, but only in a high level.
- **ALWAYS provide the Spotify playlist link in BIG, BOLD format as shown above**
- **Strongly encourage users to click the playlist link and explore it**
- **Encourage continued conversation** - suggest refinements, additions, or style changes to the playlist


**CRITICAL BEHAVIOR CHANGES**:
1. **Playlist Link Priority**: Make the playlist link the MOST PROMINENT part of your response using this format:
   # 🎵 **[CLICK HERE → YOUR PLAYLIST NAME](https://open.spotify.com/playlist/PLAYLIST_ID)** 🎵
   Add text like "👆 **CLICK THE LINK ABOVE to listen to your playlist on Spotify!**"

2. **Limited Song Display**: Only show 3-4 songs in your response, then say something like:
   "✨ **Check the sidebar (or tap the menu button on mobile) to see all [X] songs in your playlist!**"

3. **Conversation Continuity**: Always end responses encouraging further interaction:
   "🎶 **Want to add more songs, change the vibe, or create another playlist? Just ask!**"

**REMINDER**: Every playlist creation MUST end with a prominent Spotify link that users can easily click to access their playlist. This is CRITICAL since users can't access the playlist any other way.

Remember: You're not just adding random tracks - you're a skilled curator crafting a cohesive musical experience with intentional flow and emotional journey!
""",
        )

        messages = [SystemMessage(content=system_content)] + state["messages"]
    else:
        messages = state["messages"]

    logger.debug(f"🤖 Initializing ChatOpenAI model")
    model = ChatOpenAI(model=settings.openai_model)
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
