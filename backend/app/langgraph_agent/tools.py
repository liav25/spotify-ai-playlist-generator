import logging
import spotipy
import os
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_tavily import TavilySearch

from .models import Track

# Import LangSmith tracing if available
try:
    from langsmith import traceable

    tracing_enabled = os.getenv(
        "LANGSMITH_TRACING_ENABLED", "true"
    ).lower() == "true" and os.getenv("LANGSMITH_API_KEY")
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


def _normalize_track_uris(track_uris: List[str]) -> List[str]:
    """Normalize track URIs to ensure they have the correct format.

    Smaller/less capable AI models sometimes pass just the track ID instead
    of the full URI format. This function normalizes inputs to handle both cases.

    Args:
        track_uris: List of track URIs or track IDs.

    Returns:
        List of normalized track URIs in the format 'spotify:track:TRACK_ID'.
    """
    normalized = []
    for uri in track_uris:
        if not uri:
            continue

        uri = uri.strip()

        # Already a valid Spotify track URI
        if uri.startswith("spotify:track:"):
            normalized.append(uri)
        # Spotify URL format (https://open.spotify.com/track/TRACK_ID)
        elif "open.spotify.com/track/" in uri:
            try:
                track_id = uri.split("/track/")[1].split("?")[0]
                if track_id:
                    normalized.append(f"spotify:track:{track_id}")
            except (IndexError, AttributeError):
                logger.warning(f"Could not extract track ID from URL: {uri}")
        # Just a track ID (alphanumeric, typically 22 chars)
        elif uri.replace("_", "").replace("-", "").isalnum() and 15 <= len(uri) <= 30:
            normalized.append(f"spotify:track:{uri}")
        else:
            logger.warning(f"Unrecognized track URI format, skipping: {uri}")

    return normalized


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

    # Check cache first
    cache_key = f"{query}_{limit}_{market}"
    track_cache = config.get("configurable", {}).get("track_cache", {})
    if cache_key in track_cache:
        logger.info(f"🎯 Cache HIT for track search: '{query}'")
        return track_cache[cache_key]

    logger.info(f"🔍 Cache MISS for track search: '{query}' - performing search")
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

        # Write result to cache
        if track_dicts:
            config.setdefault("configurable", {}).setdefault("track_cache", {})[
                cache_key
            ] = track_dicts
            logger.info(f"💾 Cached {len(track_dicts)} tracks for query '{query}'")

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

    # Check cache first
    cache_key = f"{query}_{limit}"
    artist_cache = config.get("configurable", {}).get("artist_cache", {})
    if cache_key in artist_cache:
        logger.info(f"🎯 Cache HIT for artist search: '{query}'")
        return artist_cache[cache_key]

    logger.info(f"🔍 Cache MISS for artist search: '{query}' - performing search")
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

        # Write result to cache
        if artists:
            config.setdefault("configurable", {}).setdefault("artist_cache", {})[
                cache_key
            ] = artists
            logger.info(f"💾 Cached {len(artists)} artists for query '{query}'")

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
    config: RunnableConfig,
    seed_tracks: Optional[List[str]] = None,
    seed_artists: Optional[List[str]] = None,
    seed_genres: Optional[List[str]] = None,
    limit: int = 20,
    min_acousticness: Optional[float] = None,
    max_acousticness: Optional[float] = None,
    min_danceability: Optional[float] = None,
    max_danceability: Optional[float] = None,
    min_duration_ms: Optional[int] = None,
    max_duration_ms: Optional[int] = None,
    min_energy: Optional[float] = None,
    max_energy: Optional[float] = None,
    min_instrumentalness: Optional[float] = None,
    max_instrumentalness: Optional[float] = None,
    min_key: Optional[int] = None,
    max_key: Optional[int] = None,
    target_key: Optional[int] = None,
    min_liveness: Optional[float] = None,
    max_liveness: Optional[float] = None,
    min_loudness: Optional[float] = None,
    max_loudness: Optional[float] = None,
    min_mode: Optional[int] = None,
    max_mode: Optional[int] = None,
    min_popularity: Optional[int] = None,
    max_popularity: Optional[int] = None,
    target_popularity: Optional[int] = None,
    min_speechiness: Optional[float] = None,
    max_speechiness: Optional[float] = None,
    min_tempo: Optional[float] = None,
    max_tempo: Optional[float] = None,
    min_time_signature: Optional[int] = None,
    max_time_signature: Optional[int] = None,
    min_valence: Optional[float] = None,
    max_valence: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Get track recommendations based on seeds and tunable audio features.

    Args:
        seed_tracks: List of track IDs to base recommendations on (up to 5).
        seed_artists: List of artist IDs to base recommendations on (up to 5).
        seed_genres: List of genres to base recommendations on (up to 5).
        limit: Maximum number of recommendations to return. Default is 20.

        Audio Feature Parameters (all optional, see Spotify API docs for details):

        min_acousticness, max_acousticness: float (0.0–1.0).
        min_danceability, max_danceability: float (0.0–1.0).
        min_duration_ms, max_duration_ms, target_duration_ms: int (milliseconds).
        min_energy, max_energy: float (0.0–1.0).
        min_instrumentalness, max_instrumentalness, target_instrumentalness: float (0.0–1.0).
        min_key, max_key, target_key: int (0–11).
        min_liveness, max_liveness: float (0.0–1.0).
        min_loudness, max_loudness: float (decibels).
        min_mode, max_mode, target_mode: int (0 or 1).
        min_popularity, max_popularity: int (0–100).
        min_speechiness, max_speechiness: float (0.0–1.0).
        min_tempo, max_tempo : float (BPM).
        min_time_signature, max_time_signature : int.
        min_valence, max_valence: float (0.0–1.0).
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

        # Danceability
        if min_danceability is not None:
            audio_features["min_danceability"] = min_danceability
        if max_danceability is not None:
            audio_features["max_danceability"] = max_danceability

        # Duration
        if min_duration_ms is not None:
            audio_features["min_duration_ms"] = min_duration_ms
        if max_duration_ms is not None:
            audio_features["max_duration_ms"] = max_duration_ms

        # Energy
        if min_energy is not None:
            audio_features["min_energy"] = min_energy
        if max_energy is not None:
            audio_features["max_energy"] = max_energy

        # Instrumentalness
        if min_instrumentalness is not None:
            audio_features["min_instrumentalness"] = min_instrumentalness
        if max_instrumentalness is not None:
            audio_features["max_instrumentalness"] = max_instrumentalness

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

        # Loudness
        if min_loudness is not None:
            audio_features["min_loudness"] = min_loudness
        if max_loudness is not None:
            audio_features["max_loudness"] = max_loudness

        # Mode
        if min_mode is not None:
            audio_features["min_mode"] = min_mode
        if max_mode is not None:
            audio_features["max_mode"] = max_mode

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

        # Tempo
        if min_tempo is not None:
            audio_features["min_tempo"] = min_tempo
        if max_tempo is not None:
            audio_features["max_tempo"] = max_tempo

        # Time Signature
        if min_time_signature is not None:
            audio_features["min_time_signature"] = min_time_signature
        if max_time_signature is not None:
            audio_features["max_time_signature"] = max_time_signature

        # Valence
        if min_valence is not None:
            audio_features["min_valence"] = min_valence
        if max_valence is not None:
            audio_features["max_valence"] = max_valence

        spotify_client = config["configurable"].get("spotify_client")
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
            "description": playlist.get("description", ""),
            "public": playlist["public"],
            "collaborative": playlist["collaborative"],
            "total_tracks": 0,
            "owner": playlist.get("owner", {}).get("display_name") or "Unknown",
            "tracks": [],  # New playlist starts with empty tracks array
            "images": playlist.get("images", []),
            "external_urls": playlist.get("external_urls", {}),
        }

        logger.info(f"Successfully created playlist '{name}' with ID: {playlist['id']}")
        return playlist_data
    except Exception as e:
        logger.error(f"Error creating playlist '{name}': {e}")
        return None


@tool(
    description="Add tracks to an existing Spotify playlist and return updated playlist data",
    parse_docstring=True,
)
@traceable(name="spotify_add_tracks_to_playlist")
def add_tracks_to_playlist(
    config: RunnableConfig,
    playlist_id: str,
    track_uris: List[str],
) -> Dict[str, Any]:
    """Add tracks to an existing Spotify playlist and return updated playlist data.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.
        playlist_id: Playlist ID to add tracks to.
        track_uris: List of track URIs to add to the playlist.

    Returns:
        Dictionary containing updated playlist info with tracks, or error dict if failed.
    """
    logger.info(f"Adding {len(track_uris)} tracks to playlist {playlist_id}")

    # Normalize track URIs (handles both full URIs and plain track IDs)
    valid_uris = _normalize_track_uris(track_uris)
    if len(valid_uris) < len(track_uris):
        logger.info(
            f"Normalized {len(track_uris)} track inputs to {len(valid_uris)} valid URIs"
        )

    if not valid_uris:
        logger.error("No valid track URIs after normalization")
        return {"error": "No valid track URIs provided"}

    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return {"error": "Spotify client not available"}

        # Add tracks in chunks
        chunk_size = 100
        tracks_added = 0
        for i in range(0, len(valid_uris), chunk_size):
            chunk = valid_uris[i : i + chunk_size]
            spotify_client.playlist_add_items(playlist_id, chunk)
            tracks_added += len(chunk)
            logger.debug(
                f"Added {len(chunk)} tracks to playlist {playlist_id} (total: {tracks_added})"
            )
        logger.info(
            f"Successfully added {tracks_added} tracks to playlist {playlist_id}"
        )

        # Fetch and return updated playlist data so UI can update
        playlist_full = spotify_client.playlist(playlist_id)
        tracks_result = spotify_client.playlist_tracks(playlist_id, limit=100)

        tracks = []
        for item in tracks_result["items"]:
            if item["track"]:
                track = item["track"]
                album = track.get("album", {})
                artists = track.get("artists", [])
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
            "id": playlist_full["id"],
            "name": playlist_full["name"],
            "description": playlist_full.get("description", ""),
            "public": playlist_full["public"],
            "collaborative": playlist_full["collaborative"],
            "total_tracks": len(tracks),
            "owner": playlist_full.get("owner", {}).get("display_name") or "Unknown",
            "tracks": tracks,
            "images": playlist_full.get("images") or [],
            "external_urls": playlist_full.get("external_urls", {}),
        }

        logger.info(
            f"✅ Added {tracks_added} tracks and returning updated playlist with {len(tracks)} total tracks"
        )
        return playlist_data

    except Exception as e:
        logger.error(f"Error adding tracks to playlist {playlist_id}: {e}")
        return {"error": f"Failed to add tracks: {str(e)}"}


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
            "owner": playlist.get("owner", {}).get("display_name") or "Unknown",
            "tracks": tracks,
            "images": playlist.get("images") or [],
            "external_urls": playlist.get("external_urls", {}),
        }

        logger.info(
            f"Successfully retrieved {len(tracks)} tracks from playlist {playlist_id}"
        )
        return playlist_data
    except Exception as e:
        logger.error(f"Error getting playlist tracks for {playlist_id}: {e}")
        return {}


@tool(
    description="Create a new Spotify playlist AND add tracks to it in one operation. Returns full playlist data with tracks. This is the preferred method for playlist creation.",
    parse_docstring=True,
)
@traceable(name="spotify_create_and_populate_playlist")
def create_and_populate_playlist(
    config: RunnableConfig,
    name: str,
    track_uris: List[str],
    public: bool = True,
    description: str = "",
) -> Dict[str, Any]:
    """Create a new Spotify playlist and populate it with tracks in one operation.

    This composite tool combines playlist creation, adding tracks, and retrieving
    the final playlist data - reducing 3 API round trips to 1 tool call.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.
        name: Name of the new playlist.
        track_uris: List of track URIs to add to the playlist.
        public: Whether the playlist is public. Default is True.
        description: Playlist description. Default is empty string.

    Returns:
        Dictionary containing full playlist info with tracks (id, name, tracks with album covers),
        or error dict with 'error' key if creation failed.
    """
    logger.info(
        f"Creating and populating playlist: name='{name}', tracks={len(track_uris)}, public={public}"
    )

    # Validate inputs
    if not track_uris:
        logger.error("No track URIs provided for playlist creation")
        return {
            "error": "No tracks provided. Please gather tracks first before creating a playlist."
        }

    if not name or not name.strip():
        logger.error("Empty playlist name provided")
        return {"error": "Playlist name cannot be empty."}

    # Normalize track URIs (handles both full URIs and plain track IDs)
    valid_uris = _normalize_track_uris(track_uris)
    if len(valid_uris) < len(track_uris):
        logger.info(
            f"Normalized {len(track_uris)} track inputs to {len(valid_uris)} valid URIs"
        )

    if not valid_uris:
        logger.error("No valid Spotify track URIs found after normalization")
        return {
            "error": "No valid Spotify tracks provided. Please provide track URIs or track IDs."
        }

    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return {"error": "Spotify client not available. Please try again."}

        # Step 1: Create the playlist
        logger.info("Step 1/3: Creating playlist...")
        user_info = spotify_client.current_user()
        user_id = user_info["id"]

        playlist = spotify_client.user_playlist_create(
            user=user_id, name=name.strip(), public=public, description=description
        )
        playlist_id = playlist["id"]
        logger.info(f"✅ Created playlist '{name}' with ID: {playlist_id}")

        # Step 2: Add tracks in chunks of 100
        logger.info(f"Step 2/3: Adding {len(valid_uris)} tracks...")
        chunk_size = 100
        tracks_added = 0
        for i in range(0, len(valid_uris), chunk_size):
            chunk = valid_uris[i : i + chunk_size]
            try:
                spotify_client.playlist_add_items(playlist_id, chunk)
                tracks_added += len(chunk)
                logger.debug(
                    f"Added {len(chunk)} tracks to playlist {playlist_id} (total: {tracks_added})"
                )
            except Exception as chunk_error:
                logger.error(f"Error adding chunk {i//chunk_size + 1}: {chunk_error}")
                # Continue with remaining chunks
        logger.info(
            f"✅ Added {tracks_added}/{len(valid_uris)} tracks to playlist {playlist_id}"
        )

        # Step 3: Retrieve full playlist data with track details
        logger.info("Step 3/3: Retrieving playlist data...")
        playlist_full = spotify_client.playlist(playlist_id)
        tracks_result = spotify_client.playlist_tracks(playlist_id, limit=100)

        tracks = []
        for item in tracks_result["items"]:
            if item["track"]:
                track = item["track"]
                album = track.get("album", {})
                artists = track.get("artists", [])
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
            "id": playlist_full["id"],
            "name": playlist_full["name"],
            "description": playlist_full.get("description", ""),
            "public": playlist_full["public"],
            "collaborative": playlist_full["collaborative"],
            "total_tracks": len(tracks),
            "owner": playlist_full.get("owner", {}).get("display_name") or "Unknown",
            "tracks": tracks,
            "images": playlist_full.get("images") or [],
            "external_urls": playlist_full.get("external_urls", {}),
        }

        logger.info(
            f"✅ Successfully created and populated playlist '{name}' with {len(tracks)} tracks"
        )
        return playlist_data
    except spotipy.exceptions.SpotifyException as spotify_error:
        logger.error(f"Spotify API error creating playlist '{name}': {spotify_error}")
        return {"error": f"Spotify API error: {str(spotify_error)}. Please try again."}
    except Exception as e:
        logger.error(f"Error creating/populating playlist '{name}': {e}", exc_info=True)
        return {"error": f"Failed to create playlist: {str(e)}. Please try again."}


@tool(
    description="Remove tracks from an existing Spotify playlist using the spotipy client",
    parse_docstring=True,
)
def remove_tracks_from_playlist(
    config: RunnableConfig,
    playlist_id: str,
    track_uris: List[str],
) -> bool:
    """Remove tracks from an existing Spotify playlist.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.
        playlist_id: Playlist ID to remove tracks from.
        track_uris: List of track URIs to remove from the playlist.

    Returns:
        True if tracks were removed successfully, False otherwise.
    """
    logger.info(f"Removing {len(track_uris)} tracks from playlist {playlist_id}")
    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return False

        tracks_to_remove = [{"uri": uri} for uri in track_uris]
        spotify_client.playlist_remove_all_occurrences_of_items(
            playlist_id, [t["uri"] for t in tracks_to_remove]
        )
        logger.info(
            f"Successfully removed {len(track_uris)} tracks from playlist {playlist_id}"
        )
        return True
    except Exception as e:
        logger.error(f"Error removing tracks from playlist {playlist_id}: {e}")
        return False


@tool(
    description="Retrieve detailed audio features for a Spotify track using the spotipy client",
    parse_docstring=True,
)
def get_audio_features(
    config: RunnableConfig,
    track_id: str,
) -> Optional[Dict[str, Any]]:
    """Get audio features for a Spotify track.

    Args:
        config: Configuration containing spotify_client in a 'configurable' dict.
        track_id: The Spotify track ID.

    Returns:
        Dictionary containing audio features data (e.g., acousticness, danceability, energy, etc.),
        or None if failed.
    """
    logger.info(f"Getting audio features for track {track_id}")
    try:
        spotify_client = (
            config["configurable"].get("spotify_client") if config else None
        )
        if not spotify_client:
            logger.error("Spotify client not found in config")
            return None

        features = spotify_client.audio_features([track_id])
        if not features or not features[0]:
            logger.error(f"No audio features found for track {track_id}")
            return None

        audio_features = features[0]
        logger.info(f"Retrieved audio features for track {track_id}")
        return audio_features
    except Exception as e:
        logger.error(f"Error getting audio features for track {track_id}: {e}")
        return None


@tool(
    description="Search the web for music history, cultural context, trends, and artist information not available in Spotify",
    parse_docstring=True,
)
@traceable(name="tavily_web_search")
def tavily_search(
    query: str,
    config: RunnableConfig,
    max_results: int = 5,
) -> str:
    """Search the web for music-related information using Tavily.

    Use this tool to research:
    - Music history and genre origins
    - Cultural context for playlists
    - Time-based queries (e.g., "popular songs in 2008")
    - Emerging or indie artists not well-indexed in Spotify
    - Music trends and news
    - Context for vague user requests

    Args:
        query: Search query for music-related information.
        config: Configuration (not used but kept for consistency).
        max_results: Maximum number of search results to return. Default is 5.

    Returns:
        String containing search results with titles, URLs, and content snippets.
    """
    logger.info(f"Performing web search: query='{query}', max_results={max_results}")

    # Check cache first
    search_cache = config.get("configurable", {}).get("search_cache", {})
    if query in search_cache:
        logger.info(f"🎯 Cache HIT for Tavily search: '{query}'")
        return search_cache[query]

    logger.info(f"🔍 Cache MISS for Tavily search: '{query}' - performing search")
    try:
        search = TavilySearch(max_results=max_results, topic="general")
        results = search.invoke({"query": query})
        results_str = str(results)

        # Write result to cache
        config.setdefault("configurable", {}).setdefault("search_cache", {})[
            query
        ] = results_str
        logger.info(f"💾 Cached Tavily search for: '{query}'")

        return results_str
    except Exception as e:
        logger.error(f"Error performing web search for query '{query}': {e}")
        return f"Error: Unable to perform web search - {str(e)}"


# Export all tools for the agent
tools = [
    search_tracks,
    search_artists,
    get_artist_top_tracks,
    get_track_recommendations,
    get_available_genres,
    get_user_info,
    create_and_populate_playlist,  # Preferred: combines create + add + get in one call
    create_playlist,  # Legacy: use create_and_populate_playlist instead
    add_tracks_to_playlist,  # Legacy: use create_and_populate_playlist instead
    get_playlist_tracks,
    remove_tracks_from_playlist,
    get_audio_features,
    tavily_search,
]
