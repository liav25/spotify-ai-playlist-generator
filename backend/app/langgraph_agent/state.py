from typing import Annotated, Optional, Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_intent: Optional[str]
    playlist_id: Optional[str]
    playlist_name: Optional[str]
    playlist_data: Optional[Dict[str, Any]]
    # Caching fields to prevent redundant API calls
    search_cache: Optional[Dict[str, str]]  # Tavily results: query → results string
    track_cache: Optional[Dict[str, List[Dict[str, Any]]]]  # Track searches: query → tracks
    artist_cache: Optional[Dict[str, List[Dict[str, Any]]]]  # Artist searches: query → artists
    recommendations_cache: Optional[List[Dict[str, Any]]]  # Last recommendations
    # Context for langmem summarization (stores RunningSummary)
    context: Optional[Dict[str, Any]]