from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class Track:
    id: str
    name: str
    artist: str
    album: str
    uri: str
    popularity: int
    duration_ms: int

    @classmethod
    def from_spotify_track(cls, track_data: Dict[str, Any]) -> "Track":
        return cls(
            id=track_data["id"],
            name=track_data["name"],
            artist=", ".join([artist["name"] for artist in track_data["artists"]]),
            album=track_data["album"]["name"],
            uri=track_data["uri"],
            popularity=track_data.get("popularity", 0),
            duration_ms=track_data["duration_ms"],
        )


@dataclass
class Playlist:
    id: str
    name: str
    description: str
    url: str
    tracks: List[Track]
