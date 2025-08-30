"""
Comprehensive test suite for the get_playlist_tracks tool
"""

import pytest
from app.langgraph.tools import get_playlist_tracks


class TestGetPlaylistTracks:
    """Test suite for get_playlist_tracks tool"""

    def test_get_playlist_tracks_successful(self, config_with_spotify_client, mock_spotify_client):
        """Test successful retrieval of playlist tracks"""
        # Arrange
        playlist_id = "playlist123"
        limit = 50
        
        # Act
        result = get_playlist_tracks.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id,
            "limit": limit
        })
        
        # Assert
        assert isinstance(result, dict)
        assert result["id"] == "playlist123"
        assert result["name"] == "Test Playlist"
        assert result["total_tracks"] == 2
        assert result["owner"] == "Test User"
        assert len(result["tracks"]) == 2
        
        # Check track structure
        track = result["tracks"][0]
        assert track["id"] == "track1"
        assert track["name"] == "Playlist Track 1"
        assert track["artist"] == "Artist 1"
        assert track["album_cover"] == "https://example.com/album1.jpg"
        
        mock_spotify_client.playlist.assert_called_once_with(playlist_id)
        mock_spotify_client.playlist_tracks.assert_called_once_with(playlist_id, limit=limit)

    def test_get_playlist_tracks_default_limit(self, config_with_spotify_client, mock_spotify_client):
        """Test get_playlist_tracks with default limit"""
        # Arrange
        playlist_id = "playlist123"
        
        # Act
        result = get_playlist_tracks.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id
        })
        
        # Assert
        assert isinstance(result, dict)
        mock_spotify_client.playlist_tracks.assert_called_once_with(playlist_id, limit=100)

    def test_get_playlist_tracks_no_client(self, empty_config):
        """Test get_playlist_tracks when no Spotify client is provided"""
        # Arrange
        playlist_id = "playlist123"
        
        # Act
        result = get_playlist_tracks.invoke({
            "config": empty_config,
            "playlist_id": playlist_id
        })
        
        # Assert
        assert result == {}

    def test_get_playlist_tracks_api_error(self, config_with_spotify_client, mock_spotify_client):
        """Test get_playlist_tracks when API throws error"""
        # Arrange
        playlist_id = "error_playlist"
        mock_spotify_client.playlist.side_effect = Exception("API error")
        
        # Act
        result = get_playlist_tracks.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id
        })
        
        # Assert
        assert result == {}

    def test_get_playlist_tracks_empty_playlist(self, config_with_spotify_client, mock_spotify_client):
        """Test get_playlist_tracks with empty playlist"""
        # Arrange
        playlist_id = "empty_playlist"
        mock_spotify_client.playlist_tracks.return_value = {"items": []}
        
        # Act
        result = get_playlist_tracks.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id
        })
        
        # Assert
        assert isinstance(result, dict)
        assert result["tracks"] == []

    def test_get_playlist_tracks_missing_track_data(self, config_with_spotify_client, mock_spotify_client):
        """Test get_playlist_tracks with missing track data"""
        # Arrange
        playlist_id = "partial_playlist"
        mock_spotify_client.playlist_tracks.return_value = {
            "items": [
                {"track": None},  # Missing track
                {
                    "track": {
                        "id": "track1",
                        "name": "Valid Track",
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album", "images": []},
                        "uri": "spotify:track:track1",
                        "duration_ms": 200000,
                        "popularity": 80
                    }
                }
            ]
        }
        
        # Act
        result = get_playlist_tracks.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id
        })
        
        # Assert
        assert len(result["tracks"]) == 1  # Should skip None track