"""
Comprehensive test suite for the search_artists tool
"""

import pytest
from unittest.mock import Mock

from app.langgraph.tools import search_artists


class TestSearchArtists:
    """Test suite for search_artists tool"""

    def test_search_artists_successful(self, config_with_spotify_client, mock_spotify_client):
        """Test successful artist search"""
        # Arrange
        query = "test artist"
        limit = 5
        
        # Act
        result = search_artists.invoke(
            {"query": query, "limit": limit}, 
            config_with_spotify_client
        )
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2  # Based on mock data
        
        # Verify artist structure
        artist = result[0]
        assert artist["id"] == "artist1"
        assert artist["name"] == "Test Artist 1"
        assert artist["genres"] == ["pop", "rock"]
        assert artist["popularity"] == 85
        
        # Verify Spotify client was called correctly
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="artist", limit=limit
        )

    def test_search_artists_default_parameters(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with default parameters"""
        # Arrange
        query = "default artist"
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Verify default parameters were used
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="artist", limit=10  # Default value
        )

    def test_search_artists_custom_limit(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with custom limit"""
        # Arrange
        query = "custom artist"
        limit = 20
        
        # Act
        result = search_artists.invoke(
            {"query": query, "limit": limit},
            config_with_spotify_client
        )
        
        # Assert
        assert isinstance(result, list)
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="artist", limit=limit
        )

    def test_search_artists_no_spotify_client(self, empty_config):
        """Test search_artists when no Spotify client is provided"""
        # Arrange
        query = "test artist"
        
        # Act
        result = search_artists.invoke({"query": query}, empty_config)
        
        # Assert
        assert result == []

    def test_search_artists_spotify_api_error(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists when Spotify API throws an error"""
        # Arrange
        query = "error artist"
        mock_spotify_client.search.side_effect = Exception("Spotify API error")
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert result == []

    def test_search_artists_empty_results(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists when no artists are found"""
        # Arrange
        query = "empty artist"
        mock_spotify_client.search.return_value = {"artists": {"items": []}}
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert result == []

    def test_search_artists_missing_optional_fields(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with missing optional fields in response"""
        # Arrange
        query = "partial artist"
        mock_spotify_client.search.return_value = {
            "artists": {
                "items": [
                    {
                        "id": "artist1",
                        "name": "Partial Artist",
                        # Missing genres and popularity
                    }
                ]
            }
        }
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        
        artist = result[0]
        assert artist["id"] == "artist1"
        assert artist["name"] == "Partial Artist"
        assert artist["genres"] == []  # Default empty list
        assert artist["popularity"] == 0  # Default value

    def test_search_artists_zero_limit(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with zero limit"""
        # Arrange
        query = "zero limit artist"
        limit = 0
        
        # Act
        result = search_artists.invoke(
            {"query": query, "limit": limit},
            config_with_spotify_client
        )
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="artist", limit=limit
        )

    def test_search_artists_large_limit(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with large limit"""
        # Arrange
        query = "large limit artist"
        limit = 50  # Spotify's typical max
        
        # Act
        result = search_artists.invoke(
            {"query": query, "limit": limit},
            config_with_spotify_client
        )
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="artist", limit=limit
        )

    def test_search_artists_special_characters(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with special characters in query"""
        # Arrange
        query = "artist & band! @#$%"
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="artist", limit=10
        )
        assert isinstance(result, list)

    def test_search_artists_unicode_query(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with unicode characters"""
        # Arrange
        query = "artista español 🎵"
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="artist", limit=10
        )
        assert isinstance(result, list)

    def test_search_artists_empty_query(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with empty query"""
        # Arrange
        query = ""
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        mock_spotify_client.search.assert_called_once_with(
            q=query, type="artist", limit=10
        )

    def test_search_artists_malformed_response(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with malformed Spotify response"""
        # Arrange
        query = "malformed artist"
        mock_spotify_client.search.return_value = {"invalid": "response"}
        
        # Act & Assert
        # Should handle gracefully without crashing
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        # The exact behavior depends on implementation

    def test_search_artists_multiple_genres(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with artists having multiple genres"""
        # Arrange
        query = "multi-genre artist"
        mock_spotify_client.search.return_value = {
            "artists": {
                "items": [
                    {
                        "id": "artist1",
                        "name": "Multi-Genre Artist",
                        "genres": ["rock", "pop", "alternative", "indie"],
                        "popularity": 90
                    }
                ]
            }
        }
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert len(result) == 1
        artist = result[0]
        assert len(artist["genres"]) == 4
        assert "rock" in artist["genres"]
        assert "alternative" in artist["genres"]

    def test_search_artists_no_genres(self, config_with_spotify_client, mock_spotify_client):
        """Test search_artists with artist having no genres"""
        # Arrange
        query = "no genres artist"
        mock_spotify_client.search.return_value = {
            "artists": {
                "items": [
                    {
                        "id": "artist1",
                        "name": "No Genres Artist",
                        "genres": [],
                        "popularity": 50
                    }
                ]
            }
        }
        
        # Act
        result = search_artists.invoke({"query": query}, config_with_spotify_client)
        
        # Assert
        assert len(result) == 1
        artist = result[0]
        assert artist["genres"] == []