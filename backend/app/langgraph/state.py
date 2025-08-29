from typing import Annotated, Optional, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_intent: Optional[str]
    playlist_id: Optional[str]
    playlist_name: Optional[str]
    playlist_data: Optional[Dict[str, Any]]