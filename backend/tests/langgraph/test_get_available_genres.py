"""
Comprehensive test suite for the get_available_genres tool
"""

import pytest
from app.langgraph.tools import get_available_genres


class TestGetAvailableGenres:
    """Test suite for get_available_genres tool"""

    def test_get_available_genres_successful(self, config_with_spotify_client, mock_spotify_client):
        """Test successful retrieval of available genres"""
        # Act
        result = get_available_genres.invoke(config_with_spotify_client)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 5  # Based on mock data
        assert "pop" in result
        assert "rock" in result
        assert "hip-hop" in result
        assert "jazz" in result
        assert "classical" in result
        
        mock_spotify_client.recommendation_genre_seeds.assert_called_once()

    def test_get_available_genres_no_client(self, empty_config):
        """Test get_available_genres when no Spotify client is provided"""
        # Act
        result = get_available_genres.invoke(empty_config)
        
        # Assert
        assert result == []

    def test_get_available_genres_api_error(self, config_with_spotify_client, mock_spotify_client):
        """Test get_available_genres when API throws error"""
        # Arrange
        mock_spotify_client.recommendation_genre_seeds.side_effect = Exception("API error")
        
        # Act
        result = get_available_genres.invoke(config_with_spotify_client)
        
        # Assert
        assert result == []

    def test_get_available_genres_empty_response(self, config_with_spotify_client, mock_spotify_client):
        """Test get_available_genres with empty response"""
        # Arrange
        mock_spotify_client.recommendation_genre_seeds.return_value = {"genres": []}
        
        # Act
        result = get_available_genres.invoke(config_with_spotify_client)
        
        # Assert
        assert result == []