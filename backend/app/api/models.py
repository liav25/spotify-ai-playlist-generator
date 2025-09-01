from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class PlaylistTrack(BaseModel):
    id: str
    name: str
    artist: str
    album: str
    uri: str
    duration_ms: int
    popularity: int
    album_cover: Optional[str] = None
    preview_url: Optional[str] = None
    external_urls: Dict[str, str] = {}


class PlaylistData(BaseModel):
    id: str
    name: str
    description: str
    public: bool
    collaborative: bool
    total_tracks: int
    owner: str
    tracks: List[PlaylistTrack]
    images: Optional[List[Dict[str, Any]]] = []


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    thread_id: str
    playlist_data: Optional[PlaylistData] = None


