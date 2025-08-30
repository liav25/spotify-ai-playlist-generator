"""
Comprehensive test suite for the search_tracks tool
"""

import pytest
from unittest.mock import Mock

from app.langgraph.tools import search_tracks


class TestSearchTracks:
    """Test suite for search_tracks tool"""

    def test_search_tracks_successful(self, config_with_spotify_client, mock_spotify_client):
        """Test successful track search"""
        # Arrange
        query = "test song"
        limit = 10
        market = "US"
        
        # Act
        result = search_tracks.invoke(
            {"query": query, "limit": limit, "market": market}, 
            config_with_spotify_client
        )
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2  # Based on mock data
        
        # Verify track structure
        track = result[0]
        assert track["id"] == "track1"
        assert track["name"] == "Test Track 1"
        assert track["artist"] == "Test Artist 1"
        assert track["album"] == "Test Album 1"
        assert track["uri"] == "spotify:track:track1"
        assert track["popularity"] == 80
        assert track["duration_ms"] == 210000
        
        # Verify Spotify client was called correctly
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="track", limit=limit, market=market
        )

    def test_search_tracks_default_parameters(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks with default parameters"""
        # Arrange
        query = "default test"
        
        # Act
        result = search_tracks.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Verify default parameters were used
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="track", limit=20, market="US"  # Default values
        )

    def test_search_tracks_custom_parameters(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks with custom parameters"""
        # Arrange
        query = "custom test"
        limit = 5
        market = "UK"
        
        # Act
        result = search_tracks.invoke(
            {"query": query, "limit": limit, "market": market},
            config_with_spotify_client
        )
        
        # Assert
        assert isinstance(result, list)
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="track", limit=limit, market=market
        )

    def test_search_tracks_no_spotify_client(self, empty_config):
        """Test search_tracks when no Spotify client is provided"""
        # Arrange
        query = "test song"
        
        # Act
        result = search_tracks.invoke({"query": query}, empty_config)
        
        # Assert
        assert result == []

    def test_search_tracks_spotify_api_error(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks when Spotify API throws an error"""
        # Arrange
        query = "error test"
        mock_spotify_client.search.side_effect = Exception("Spotify API error")
        
        # Act
        result = search_tracks.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert result == []

    def test_search_tracks_empty_results(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks when no tracks are found"""
        # Arrange
        query = "empty test"
        mock_spotify_client.search.return_value = {"tracks": {"items": []}}
        
        # Act
        result = search_tracks.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert result == []

    def test_search_tracks_malformed_response(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks with malformed Spotify response"""
        # Arrange
        query = "malformed test"
        mock_spotify_client.search.return_value = {"invalid": "response"}
        
        # Act & Assert
        # Should handle gracefully and not crash
        result = search_tracks.invoke({"query": query}, config_with_spotify_client)
        # The exact behavior depends on implementation, but it shouldn't crash

    def test_search_tracks_partial_track_data(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks with partial track data from Spotify"""
        # Arrange
        query = "partial test"
        mock_spotify_client.search.return_value = {
            "tracks": {
                "items": [
                    {
                        "id": "track1",
                        "name": "Partial Track",
                        "artists": [{"name": "Partial Artist"}],
                        "album": {"name": "Partial Album"},
                        "uri": "spotify:track:track1",
                        # Missing popularity and duration_ms
                    }
                ]
            }
        }
        
        # Act
        result = search_tracks.invoke({"query": query}, config_with_spotify_client)
        
        # Assert - should handle missing fields gracefully
        assert isinstance(result, list)
        if result:  # If the tool handles partial data
            track = result[0]
            assert "id" in track
            assert "name" in track

    def test_search_tracks_large_limit(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks with a large limit value"""
        # Arrange
        query = "large limit test"
        limit = 50  # Spotify's max is usually 50
        
        # Act
        result = search_tracks.invoke(
            {"query": query, "limit": limit}, 
            config_with_spotify_client
        )
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="track", limit=limit, market="US"
        )

    def test_search_tracks_special_characters_query(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks with special characters in query"""
        # Arrange
        query = "test & song! @#$%"
        
        # Act
        result = search_tracks.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="track", limit=20, market="US"
        )
        assert isinstance(result, list)

    def test_search_tracks_empty_query(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks with empty query"""
        # Arrange
        query = ""
        
        # Act
        result = search_tracks.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="track", limit=20, market="US"
        )

    def test_search_tracks_unicode_query(self, config_with_spotify_client, mock_spotify_client):
        """Test search_tracks with unicode characters in query"""
        # Arrange
        query = "café música 🎵"
        
        # Act
        result = search_tracks.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="track", limit=20, market="US"
        )
        assert isinstance(result, list)