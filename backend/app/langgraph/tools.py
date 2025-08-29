import logging
import spotipy
import os
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from .models import Track

# Import LangSmith tracing if available
try:
    from langsmith import traceable
    tracing_enabled = os.getenv("LANGSMITH_TRACING_ENABLED", "true").lower() == "true" and os.getenv("LANGSMITH_API_KEY")
    if tracing_enabled:
        print("✅ LangSmith tracing enabled for Spotify tools")
    else:
        print("ℹ️  LangSmith tracing disabled for Spotify tools")
except ImportError:
    print("⚠️  LangSmith not available for tools tracing")
    traceable = lambda name: lambda func: func  # No-op decorator
    tracing_enabled = False

logger = logging.getLogger(__name__)


def _track_to_dict(track: Track) -> Dict[str, Any]:
    """Convert a Track object to a dictionary.

    Args:
        track: The Track object.

    Returns:
        A dictionary representation of the Track.
    """
    return {
        "id": track.id,
        "name": track.name,
        "artist": track.artist,
        "album": track.album,
        "uri": track.uri,
        "popularity": track.popularity,
        "duration_ms": track.duration_ms,
    }


@tool(
    description="Find tracks on Spotify by searching for song names, artists, or keywords",
    parse_docstring=True,
)
@traceable(name="spotify_search_tracks")
def search_tracks(
    query: str,
    config: RunnableConfig,
    limit: int = 20,
    market: str = "US",
) -> List[Dict[str, Any]]:
    """Search Spotify for tracks matching the query.

    Args:
        query: Search query (song name, artist, or keywords).
        config: Configuration containing spotify_client in a 'configurable' dict.
        limit: Maximum number of tracks to return. Default is 20.
        market: Country code for market-specific results. Default is 'US'.

    Returns:
        A list of dictionaries, each containing: id, name, artist, album, uri, popularity, and duration_ms.
    """
    logger.info(f"Searching tracks: query='{query}', limit={limit}, market={market}")
    try:
        spotify_client = config["configurable"].get("spotify_client")
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return []

        results = spotify_client.search(
            q=query, type="track", limit=limit, market=market
        )
        tracks = [Track.from_spotify_track(item) for item in results["tracks"]["items"]]
        track_dicts = [_track_to_dict(track) for track in tracks]
        logger.info(f"Found {len(track_dicts)} tracks for query '{query}'")
        return track_dicts
    except Exception as e:
        logger.error(f"Error searching tracks for query '{query}': {e}")
        return []


@tool(
    description="Find artists on Spotify by searching for artist names or related terms",
    parse_docstring=True,
)
def search_artists(
    query: str,
    config: RunnableConfig,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Search for artists on Spotify.

    Args:
        query: Artist search query (artist name or related terms).
        config: Configuration containing spotify_client in a 'configurable' dict.
        limit: Maximum number of artists to return. Default is 10.

    Returns:
        A list of dictionaries, each containing: id, name, genres, and popularity.
    """
    logger.info(f"Searching artists: query='{query}', limit={limit}")
    try:
        spotify_client = config["configurable"].get("spotify_client")
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return []

        results = spotify_client.search(q=query, type="artist", limit=limit)
        artists = [
            {
                "id": item["id"],
                "name": item["name"],
                "genres": item.get("genres", []),
                "popularity": item.get("popularity", 0),
            }
            for item in results["artists"]["items"]
        ]
        logger.info(f"Found {len(artists)} artists for query '{query}'")
        return artists
    except Exception as e:
        logger.error(f"Error searching artists for query '{query}': {e}")
        return []


@tool(
    description="Retrieve the most popular tracks for a specific artist",
    parse_docstring=True,
)
def get_artist_top_tracks(
    artist_id: str,
    config: RunnableConfig,
    country: str = "US",
) -> List[Dict[str, Any]]:
    """Get an artist's top tracks based on popularity.

    Args:
        artist_id: Spotify artist ID.
        config: Configuration containing spotify_client in a 'configurable' dict.
        country: Country code for market-specific top tracks. Default is 'US'.

    Returns:
        A list of dictionaries, each containing: id, name, artist, album, uri, popularity, duration_ms.
    """
    logger.info(
        f"Getting top tracks for artist: artist_id={artist_id}, country={country}"
    )
    try:
        spotify_client = config["configurable"].get("spotify_client")
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return []

        results = spotify_client.artist_top_tracks(artist_id, country=country)
        tracks = [Track.from_spotify_track(item) for item in results["tracks"]]
        track_dicts = [_track_to_dict(track) for track in tracks]
        logger.info(f"Found {len(track_dicts)} top tracks for artist {artist_id}")
        return track_dicts
    except Exception as e:
        logger.error(f"Error getting top tracks for artist {artist_id}: {e}")
        return []


@tool(
    description="Generate personalized track recommendations using seed tracks, artists, or genres with fine-tuned audio features",
    parse_docstring=True,
)
def get_track_recommendations(
    seed_tracks: Optional[List[str]] = None,
    seed_artists: Optional[List[str]] = None,
    seed_genres: Optional[List[str]] = None,
    limit: int = 20,
    min_acousticness: Optional[float] = None,
    max_acousticness: Optional[float] = None,
    target_acousticness: Optional[float] = None,
    min_danceability: Optional[float] = None,
    max_danceability: Optional[float] = None,
    target_danceability: Optional[float] = None,
    min_duration_ms: Optional[int] = None,
    max_duration_ms: Optional[int] = None,
    target_duration_ms: Optional[int] = None,
    min_energy: Optional[float] = None,
    max_energy: Optional[float] = None,
    target_energy: Optional[float] = None,
    min_instrumentalness: Optional[float] = None,
    max_instrumentalness: Optional[float] = None,
    target_instrumentalness: Optional[float] = None,
    min_key: Optional[int] = None,
    max_key: Optional[int] = None,
    target_key: Optional[int] = None,
    min_liveness: Optional[float] = None,
    max_liveness: Optional[float] = None,
    target_liveness: Optional[float] = None,
    min_loudness: Optional[float] = None,
    max_loudness: Optional[float] = None,
    target_loudness: Optional[float] = None,
    min_mode: Optional[int] = None,
    max_mode: Optional[int] = None,
    target_mode: Optional[int] = None,
    min_popularity: Optional[int] = None,
    max_popularity: Optional[int] = None,
    target_popularity: Optional[int] = None,
    min_speechiness: Optional[float] = None,
    max_speechiness: Optional[float] = None,
    target_speechiness: Optional[float] = None,
    min_tempo: Optional[float] = None,
    max_tempo: Optional[float] = None,
    target_tempo: Optional[float] = None,
    min_time_signature: Optional[int] = None,
    max_time_signature: Optional[int] = None,
    target_time_signature: Optional[int] = None,
    min_valence: Optional[float] = None,
    max_valence: Optional[float] = None,
    target_valence: Optional[float] = None,
    config: Optional[RunnableConfig] = None,
) -> List[Dict[str, Any]]:
    """Get track recommendations based on seeds and tunable audio features.

    Args:
        seed_tracks: List of track IDs to base recommendations on (up to 5).
        seed_artists: List of artist IDs to base recommendations on (up to 5).
        seed_genres: List of genres to base recommendations on (up to 5).
        limit: Maximum number of recommendations to return. Default is 20.

        Audio Feature Parameters (all optional, see Spotify API docs for details):

        min_acousticness, max_acousticness, target_acousticness: float (0.0–1.0).
        min_danceability, max_danceability, target_danceability: float (0.0–1.0).
        min_duration_ms, max_duration_ms, target_duration_ms: int (milliseconds).
        min_energy, max_energy, target_energy: float (0.0–1.0).
        min_instrumentalness, max_instrumentalness, target_instrumentalness: float (0.0–1.0).
        min_key, max_key, target_key: int (0–11).
        min_liveness, max_liveness, target_liveness: float (0.0–1.0).
        min_loudness, max_loudness, target_loudness: float (decibels).
        min_mode, max_mode, target_mode: int (0 or 1).
        min_popularity, max_popularity, target_popularity: int (0–100).
        min_speechiness, max_speechiness, target_speechiness: float (0.0–1.0).
        min_tempo, max_tempo, target_tempo: float (BPM).
        min_time_signature, max_time_signature, target_time_signature: int.
        min_valence, max_valence, target_valence: float (0.0–1.0).
        config: Configuration containing spotify_client in a 'configurable' dict.

    Returns:
        A list of dictionaries, each containing: id, name, artist, album, uri, popularity, duration_ms.
    """
    logger.info(
        f"Getting recommendations: seed_tracks={seed_tracks}, seed_artists={seed_artists}, seed_genres={seed_genres}, limit={limit}"
    )
    try:
        # Build kwargs for non-None audio features
        audio_features = {}

        # Acousticness
        if min_acousticness is not None:
            audio_features["min_acousticness"] = min_acousticness
        if max_acousticness is not None:
            audio_features["max_acousticness"] = max_acousticness
        if target_acousticness is not None:
            audio_features["target_acousticness"] = target_acousticness

        # Danceability
        if min_danceability is not None:
            audio_features["min_danceability"] = min_danceability
        if max_danceability is not None:
            audio_features["max_danceability"] = max_danceability
        if target_danceability is not None:
            audio_features["target_danceability"] = target_danceability

        # Duration
        if min_duration_ms is not None:
            audio_features["min_duration_ms"] = min_duration_ms
        if max_duration_ms is not None:
            audio_features["max_duration_ms"] = max_duration_ms
        if target_duration_ms is not None:
            audio_features["target_duration_ms"] = target_duration_ms

        # Energy
        if min_energy is not None:
            audio_features["min_energy"] = min_energy
        if max_energy is not None:
            audio_features["max_energy"] = max_energy
        if target_energy is not None:
            audio_features["target_energy"] = target_energy

        # Instrumentalness
        if min_instrumentalness is not None:
            audio_features["min_instrumentalness"] = min_instrumentalness
        if max_instrumentalness is not None:
            audio_features["max_instrumentalness"] = max_instrumentalness
        if target_instrumentalness is not None:
            audio_features["target_instrumentalness"] = target_instrumentalness

        # Key
        if min_key is not None:
            audio_features["min_key"] = min_key
        if max_key is not None:
            audio_features["max_key"] = max_key
        if target_key is not None:
            audio_features["target_key"] = target_key

        # Liveness
        if min_liveness is not None:
            audio_features["min_liveness"] = min_liveness
        if max_liveness is not None:
            audio_features["max_liveness"] = max_liveness
        if target_liveness is not None:
            audio_features["target_liveness"] = target_liveness

        # Loudness
        if min_loudness is not None:
            audio_features["min_loudness"] = min_loudness
        if max_loudness is not None:
            audio_features["max_loudness"] = max_loudness
        if target_loudness is not None:
            audio_features["target_loudness"] = target_loudness

        # Mode
        if min_mode is not None:
            audio_features["min_mode"] = min_mode
        if max_mode is not None:
            audio_features["max_mode"] = max_mode
        if target_mode is not None:
            audio_features["target_mode"] = target_mode

        # Popularity
        if min_popularity is not None:
            audio_features["min_popularity"] = min_popularity
        if max_popularity is not None:
            audio_features["max_popularity"] = max_popularity
        if target_popularity is not None:
            audio_features["target_popularity"] = target_popularity

        # Speechiness
        if min_speechiness is not None:
            audio_features["min_speechiness"] = min_speechiness
        if max_speechiness is not None:
            audio_features["max_speechiness"] = max_speechiness
        if target_speechiness is not None:
            audio_features["target_speechiness"] = target_speechiness

        # Tempo
        if min_tempo is not None:
            audio_features["min_tempo"] = min_tempo
        if max_tempo is not None:
            audio_features["max_tempo"] = max_tempo
        if target_tempo is not None:
            audio_features["target_tempo"] = target_tempo

        # Time Signature
        if min_time_signature is not None:
            audio_features["min_time_signature"] = min_time_signature
        if max_time_signature is not None:
            audio_features["max_time_signature"] = max_time_signature
        if target_time_signature is not None:
            audio_features["target_time_signature"] = target_time_signature

        # Valence
        if min_valence is not None:
            audio_features["min_valence"] = min_valence
        if max_valence is not None:
            audio_features["max_valence"] = max_valence
        if target_valence is not None:
            audio_features["target_valence"] = target_valence

        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return []

        results = spotify_client.recommendations(
            seed_tracks=seed_tracks,
            seed_artists=seed_artists,
            seed_genres=seed_genres,
            limit=limit,
            **audio_features,
        )
        tracks = [Track.from_spotify_track(item) for item in results["tracks"]]
        track_dicts = [_track_to_dict(track) for track in tracks]
        logger.info(f"Found {len(track_dicts)} recommendations")
        return track_dicts
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return []


@tool(
    description="Retrieve all available music genres that can be used as recommendation seeds",
    parse_docstring=True,
)
def get_available_genres(
    config: RunnableConfig,
) -> List[str]:
    """Get list of available genres for recommendations.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.

    Returns:
        A list of available genre strings that can be used as seed_genres in recommendations.
    """
    logger.info("Getting available genres")
    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return []

        genres = spotify_client.recommendation_genre_seeds()
        genre_list = genres["genres"]
        logger.info(f"Found {len(genre_list)} available genres")
        return genre_list
    except Exception as e:
        logger.error(f"Error getting available genres: {e}")
        return []


@tool(
    description="Get current Spotify user information",
    parse_docstring=True,
)
def get_user_info(config: RunnableConfig) -> Optional[Dict[str, Any]]:
    """Get current Spotify user information.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.

    Returns:
        Dictionary with current user info (id, display_name, followers, country), or None if failed.
    """
    logger.info("Getting current user information")
    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return None
            
        user_info = spotify_client.current_user()
        user_data = {
            "id": user_info.get("id"),
            "display_name": user_info.get("display_name"),
            "followers": user_info.get("followers", {}).get("total", 0),
            "country": user_info.get("country"),
        }
        logger.info(
            f"Retrieved user info for: {user_data['display_name']} ({user_data['id']})"
        )
        return user_data
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return None


@tool(
    description="Create a new Spotify playlist using the spotipy client",
    parse_docstring=True,
)
@traceable(name="spotify_create_playlist")
def create_playlist(
    config: RunnableConfig,
    name: str,
    public: bool = True,
    description: str = "",
) -> Optional[Dict[str, Any]]:
    """Create a new Spotify playlist for the current user.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.
        name: Name of the new playlist.
        public: Whether the playlist is public. Default is True.
        description: Playlist description. Default is empty string.

    Returns:
        Dictionary containing playlist info (id, name, url), or None if creation failed.
    """
    logger.info(f"Creating playlist: name='{name}', public={public}")
    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return None
            
        user_info = spotify_client.current_user()
        user_id = user_info["id"]

        playlist = spotify_client.user_playlist_create(
            user=user_id, name=name, public=public, description=description
        )
        
        playlist_data = {
            "id": playlist["id"],
            "name": playlist["name"],
            "url": playlist["external_urls"]["spotify"],
            "public": playlist["public"],
            "collaborative": playlist["collaborative"],
            "description": playlist.get("description", ""),
            "owner": playlist["owner"]["display_name"],
            "tracks": 0  # New playlist starts with 0 tracks
        }
        
        logger.info(f"Successfully created playlist '{name}' with ID: {playlist['id']}")
        return playlist_data
    except Exception as e:
        logger.error(f"Error creating playlist '{name}': {e}")
        return None


@tool(
    description="Add tracks to an existing Spotify playlist using the spotipy client",
    parse_docstring=True,
)
@traceable(name="spotify_add_tracks_to_playlist")
def add_tracks_to_playlist(
    config: RunnableConfig,
    playlist_id: str,
    track_uris: List[str],
) -> bool:
    """Add tracks to an existing Spotify playlist.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.
        playlist_id: Playlist ID to add tracks to.
        track_uris: List of track URIs to add to the playlist.

    Returns:
        True if tracks were added successfully, False otherwise.
    """
    logger.info(f"Adding {len(track_uris)} tracks to playlist {playlist_id}")
    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return False
            
        chunk_size = 100
        chunks_processed = 0
        for i in range(0, len(track_uris), chunk_size):
            chunk = track_uris[i : i + chunk_size]
            spotify_client.playlist_add_items(playlist_id, chunk)
            chunks_processed += 1
            logger.debug(
                f"Added chunk {chunks_processed} ({len(chunk)} tracks) to playlist {playlist_id}"
            )
        logger.info(
            f"Successfully added all {len(track_uris)} tracks to playlist {playlist_id}"
        )
        return True
    except Exception as e:
        logger.error(f"Error adding tracks to playlist {playlist_id}: {e}")
        return False


@tool(
    description="Retrieve tracks from a Spotify playlist with album cover information",
    parse_docstring=True,
)
def get_playlist_tracks(
    config: RunnableConfig,
    playlist_id: str,
    limit: int = 100,
) -> Dict[str, Any]:
    """Get tracks from a Spotify playlist including album cover information.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.
        playlist_id: Playlist ID to retrieve tracks from.
        limit: Maximum number of tracks to return. Default is 100.

    Returns:
        Dictionary containing playlist info and tracks with album covers, or empty dict if failed.
    """
    logger.info(f"Getting tracks from playlist {playlist_id}")
    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return {}

        # Get playlist info
        playlist = spotify_client.playlist(playlist_id)
        
        # Get playlist tracks
        tracks_result = spotify_client.playlist_tracks(playlist_id, limit=limit)
        
        tracks = []
        for item in tracks_result["items"]:
            if item["track"]:  # Check if track exists
                track = item["track"]
                album = track.get("album", {})
                artists = track.get("artists", [])
                
                # Extract album cover URLs
                album_images = album.get("images", [])
                album_cover = album_images[0]["url"] if album_images else None
                
                track_data = {
                    "id": track["id"],
                    "name": track["name"],
                    "artist": ", ".join([artist["name"] for artist in artists]),
                    "album": album.get("name", ""),
                    "uri": track["uri"],
                    "duration_ms": track["duration_ms"],
                    "popularity": track.get("popularity", 0),
                    "album_cover": album_cover,
                    "preview_url": track.get("preview_url"),
                    "external_urls": track.get("external_urls", {}),
                }
                tracks.append(track_data)

        playlist_data = {
            "id": playlist["id"],
            "name": playlist["name"],
            "description": playlist.get("description", ""),
            "public": playlist["public"],
            "collaborative": playlist["collaborative"],
            "total_tracks": playlist["tracks"]["total"],
            "owner": playlist["owner"]["display_name"],
            "tracks": tracks,
            "images": playlist.get("images", []),
        }
        
        logger.info(f"Successfully retrieved {len(tracks)} tracks from playlist {playlist_id}")
        return playlist_data
    except Exception as e:
        logger.error(f"Error getting playlist tracks for {playlist_id}: {e}")
        return {}


# Export all tools for the agent
tools = [
    search_tracks,
    search_artists,
    get_artist_top_tracks,
    get_track_recommendations,
    get_available_genres,
    get_user_info,
    create_playlist,
    add_tracks_to_playlist,
    get_playlist_tracks,
]