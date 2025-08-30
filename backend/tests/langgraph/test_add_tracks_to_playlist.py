"""
Comprehensive test suite for the add_tracks_to_playlist tool
"""

import pytest
from app.langgraph.tools import add_tracks_to_playlist


class TestAddTracksToPlaylist:
    """Test suite for add_tracks_to_playlist tool"""

    def test_add_tracks_to_playlist_successful(self, config_with_spotify_client, mock_spotify_client):
        """Test successful addition of tracks to playlist"""
        # Arrange
        playlist_id = "playlist123"
        track_uris = ["spotify:track:track1", "spotify:track:track2"]
        
        # Act
        result = add_tracks_to_playlist.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id,
            "track_uris": track_uris
        })
        
        # Assert
        assert result is True
        mock_spotify_client.playlist_add_items.assert_called_once_with(playlist_id, track_uris)

    def test_add_tracks_to_playlist_large_batch(self, config_with_spotify_client, mock_spotify_client):
        """Test adding a large batch of tracks (testing chunking)"""
        # Arrange
        playlist_id = "playlist123"
        track_uris = [f"spotify:track:track{i}" for i in range(150)]  # > 100 tracks
        
        # Act
        result = add_tracks_to_playlist.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id,
            "track_uris": track_uris
        })
        
        # Assert
        assert result is True
        # Should be called twice due to chunking (100 + 50)
        assert mock_spotify_client.playlist_add_items.call_count == 2

    def test_add_tracks_to_playlist_no_client(self, empty_config):
        """Test add_tracks_to_playlist when no Spotify client is provided"""
        # Arrange
        playlist_id = "playlist123"
        track_uris = ["spotify:track:track1"]
        
        # Act
        result = add_tracks_to_playlist.invoke({
            "config": empty_config,
            "playlist_id": playlist_id,
            "track_uris": track_uris
        })
        
        # Assert
        assert result is False

    def test_add_tracks_to_playlist_api_error(self, config_with_spotify_client, mock_spotify_client):
        """Test add_tracks_to_playlist when API throws error"""
        # Arrange
        playlist_id = "error_playlist"
        track_uris = ["spotify:track:track1"]
        mock_spotify_client.playlist_add_items.side_effect = Exception("API error")
        
        # Act
        result = add_tracks_to_playlist.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id,
            "track_uris": track_uris
        })
        
        # Assert
        assert result is False

    def test_add_tracks_to_playlist_empty_list(self, config_with_spotify_client, mock_spotify_client):
        """Test adding empty list of tracks"""
        # Arrange
        playlist_id = "playlist123"
        track_uris = []
        
        # Act
        result = add_tracks_to_playlist.invoke({
            "config": config_with_spotify_client,
            "playlist_id": playlist_id,
            "track_uris": track_uris
        })
        
        # Assert
        assert result is True
        mock_spotify_client.playlist_add_items.assert_not_called()