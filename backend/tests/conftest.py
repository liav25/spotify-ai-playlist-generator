"""
Pytest configuration and fixtures for testing Spotify agent tools
"""

import pytest
from unittest.mock import Mock, MagicMock
from langchain_core.runnables import RunnableConfig


@pytest.fixture
def mock_spotify_client():
    """Create a mock Spotify client for testing"""
    client = Mock()
    
    # Mock search results
    client.search.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "track1",
                    "name": "Test Track 1",
                    "artists": [{"name": "Test Artist 1"}],
                    "album": {"name": "Test Album 1"},
                    "uri": "spotify:track:track1",
                    "popularity": 80,
                    "duration_ms": 210000,
                },
                {
                    "id": "track2",
                    "name": "Test Track 2",
                    "artists": [{"name": "Test Artist 2"}],
                    "album": {"name": "Test Album 2"},
                    "uri": "spotify:track:track2",
                    "popularity": 70,
                    "duration_ms": 180000,
                }
            ]
        },
        "artists": {
            "items": [
                {
                    "id": "artist1",
                    "name": "Test Artist 1",
                    "genres": ["pop", "rock"],
                    "popularity": 85,
                },
                {
                    "id": "artist2",
                    "name": "Test Artist 2",
                    "genres": ["indie", "alternative"],
                    "popularity": 75,
                }
            ]
        }
    }
    
    # Mock artist top tracks
    client.artist_top_tracks.return_value = {
        "tracks": [
            {
                "id": "top1",
                "name": "Top Track 1",
                "artists": [{"name": "Test Artist"}],
                "album": {"name": "Top Album 1"},
                "uri": "spotify:track:top1",
                "popularity": 95,
                "duration_ms": 240000,
            }
        ]
    }
    
    # Mock recommendations
    client.recommendations.return_value = {
        "tracks": [
            {
                "id": "rec1",
                "name": "Recommended Track 1",
                "artists": [{"name": "Recommended Artist 1"}],
                "album": {"name": "Recommended Album 1"},
                "uri": "spotify:track:rec1",
                "popularity": 85,
                "duration_ms": 200000,
            }
        ]
    }
    
    # Mock available genres
    client.recommendation_genre_seeds.return_value = {
        "genres": ["pop", "rock", "hip-hop", "jazz", "classical"]
    }
    
    # Mock current user
    client.current_user.return_value = {
        "id": "test_user",
        "display_name": "Test User",
        "followers": {"total": 100},
        "country": "US"
    }
    
    # Mock playlist creation
    client.user_playlist_create.return_value = {
        "id": "playlist123",
        "name": "Test Playlist",
        "description": "Test Description",
        "public": True,
        "collaborative": False,
        "owner": {"display_name": "Test User"},
        "images": []
    }
    
    # Mock playlist tracks addition
    client.playlist_add_items.return_value = {"snapshot_id": "abc123"}
    
    # Mock playlist details and tracks
    client.playlist.return_value = {
        "id": "playlist123",
        "name": "Test Playlist",
        "description": "Test Description",
        "public": True,
        "collaborative": False,
        "tracks": {"total": 2},
        "owner": {"display_name": "Test User"},
        "images": [{"url": "https://example.com/playlist.jpg"}]
    }
    
    client.playlist_tracks.return_value = {
        "items": [
            {
                "track": {
                    "id": "track1",
                    "name": "Playlist Track 1",
                    "artists": [{"name": "Artist 1"}],
                    "album": {
                        "name": "Album 1",
                        "images": [{"url": "https://example.com/album1.jpg"}]
                    },
                    "uri": "spotify:track:track1",
                    "duration_ms": 210000,
                    "popularity": 80,
                    "preview_url": "https://example.com/preview1.mp3",
                    "external_urls": {"spotify": "https://open.spotify.com/track/track1"}
                }
            },
            {
                "track": {
                    "id": "track2",
                    "name": "Playlist Track 2", 
                    "artists": [{"name": "Artist 2"}],
                    "album": {
                        "name": "Album 2",
                        "images": [{"url": "https://example.com/album2.jpg"}]
                    },
                    "uri": "spotify:track:track2",
                    "duration_ms": 180000,
                    "popularity": 70,
                    "preview_url": "https://example.com/preview2.mp3",
                    "external_urls": {"spotify": "https://open.spotify.com/track/track2"}
                }
            }
        ]
    }
    
    return client


@pytest.fixture
def config_with_spotify_client(mock_spotify_client):
    """Create a RunnableConfig with mock Spotify client"""
    return RunnableConfig(
        configurable={"spotify_client": mock_spotify_client}
    )


@pytest.fixture
def empty_config():
    """Create an empty RunnableConfig for testing error cases"""
    return RunnableConfig(configurable={})


# Sample test data
@pytest.fixture
def sample_track_data():
    """Sample track data for testing"""
    return {
        "id": "track1",
        "name": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album", 
        "uri": "spotify:track:track1",
        "popularity": 80,
        "duration_ms": 210000
    }


@pytest.fixture
def sample_artist_data():
    """Sample artist data for testing"""
    return {
        "id": "artist1",
        "name": "Test Artist",
        "genres": ["pop", "rock"],
        "popularity": 85
    }


@pytest.fixture
def sample_playlist_data():
    """Sample playlist data for testing"""
    return {
        "id": "playlist123",
        "name": "Test Playlist",
        "description": "Test Description",
        "public": True,
        "collaborative": False,
        "total_tracks": 2,
        "owner": "Test User",
        "tracks": [
            {
                "id": "track1",
                "name": "Playlist Track 1",
                "artist": "Artist 1",
                "album": "Album 1",
                "uri": "spotify:track:track1",
                "duration_ms": 210000,
                "popularity": 80,
                "album_cover": "https://example.com/album1.jpg",
                "preview_url": "https://example.com/preview1.mp3",
                "external_urls": {"spotify": "https://open.spotify.com/track/track1"}
            }
        ],
        "images": [{"url": "https://example.com/playlist.jpg"}]
    }