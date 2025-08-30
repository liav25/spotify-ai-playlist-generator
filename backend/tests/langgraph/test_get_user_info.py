"""
Comprehensive test suite for the get_user_info tool
"""

import pytest
from app.langgraph.tools import get_user_info


class TestGetUserInfo:
    """Test suite for get_user_info tool"""

    def test_get_user_info_successful(self, config_with_spotify_client, mock_spotify_client):
        """Test successful retrieval of user information"""
        # Act
        result = get_user_info.invoke(config_with_spotify_client)
        
        # Assert
        assert isinstance(result, dict)
        assert result["id"] == "test_user"
        assert result["display_name"] == "Test User"
        assert result["followers"] == 100
        assert result["country"] == "US"
        
        mock_spotify_client.current_user.assert_called_once()

    def test_get_user_info_no_client(self, empty_config):
        """Test get_user_info when no Spotify client is provided"""
        # Act
        result = get_user_info.invoke(empty_config)
        
        # Assert
        assert result is None

    def test_get_user_info_api_error(self, config_with_spotify_client, mock_spotify_client):
        """Test get_user_info when API throws error"""
        # Arrange
        mock_spotify_client.current_user.side_effect = Exception("API error")
        
        # Act
        result = get_user_info.invoke(config_with_spotify_client)
        
        # Assert
        assert result is None

    def test_get_user_info_partial_data(self, config_with_spotify_client, mock_spotify_client):
        """Test get_user_info with partial user data"""
        # Arrange
        mock_spotify_client.current_user.return_value = {
            "id": "partial_user",
            "display_name": "Partial User",
            # Missing followers and country
        }
        
        # Act
        result = get_user_info.invoke(config_with_spotify_client)
        
        # Assert
        assert result["id"] == "partial_user"
        assert result["display_name"] == "Partial User"
        assert result["followers"] == 0  # Default
        assert result["country"] is None  # Default