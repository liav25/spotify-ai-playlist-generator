"""
Comprehensive test suite for the create_playlist tool
"""

import pytest
from app.langgraph.tools import create_playlist


class TestCreatePlaylist:
    """Test suite for create_playlist tool"""

    def test_create_playlist_successful(self, config_with_spotify_client, mock_spotify_client):
        """Test successful playlist creation"""
        # Arrange
        name = "My Test Playlist"
        public = True
        description = "A test playlist"
        
        # Act
        result = create_playlist.invoke({
            "config": config_with_spotify_client,
            "name": name,
            "public": public,
            "description": description
        })
        
        # Assert
        assert isinstance(result, dict)
        assert result["id"] == "playlist123"
        assert result["name"] == "Test Playlist"
        assert result["public"] is True
        assert result["collaborative"] is False
        assert result["total_tracks"] == 0
        assert result["owner"] == "Test User"
        assert result["tracks"] == []
        
        # Verify API calls
        mock_spotify_client.current_user.assert_called_once()
        mock_spotify_client.user_playlist_create.assert_called_once()

    def test_create_playlist_default_parameters(self, config_with_spotify_client, mock_spotify_client):
        """Test create_playlist with default parameters"""
        # Arrange
        name = "Default Playlist"
        
        # Act
        result = create_playlist.invoke({
            "config": config_with_spotify_client,
            "name": name
        })
        
        # Assert
        assert isinstance(result, dict)
        assert result["name"] == "Test Playlist"

    def test_create_playlist_no_client(self, empty_config):
        """Test create_playlist when no Spotify client is provided"""
        # Arrange
        name = "Test Playlist"
        
        # Act
        result = create_playlist.invoke({
            "config": empty_config,
            "name": name
        })
        
        # Assert
        assert result is None

    def test_create_playlist_api_error(self, config_with_spotify_client, mock_spotify_client):
        """Test create_playlist when API throws error"""
        # Arrange
        name = "Error Playlist"
        mock_spotify_client.user_playlist_create.side_effect = Exception("API error")
        
        # Act
        result = create_playlist.invoke({
            "config": config_with_spotify_client,
            "name": name
        })
        
        # Assert
        assert result is None

    def test_create_playlist_private(self, config_with_spotify_client, mock_spotify_client):
        """Test creating a private playlist"""
        # Arrange
        name = "Private Playlist"
        public = False
        
        # Act
        result = create_playlist.invoke({
            "config": config_with_spotify_client,
            "name": name,
            "public": public
        })
        
        # Assert
        assert isinstance(result, dict)
        # Note: The actual public flag comes from the mock response