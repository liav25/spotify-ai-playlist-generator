"""
Comprehensive test suite for the get_track_recommendations tool
"""

import pytest
from app.langgraph.tools import get_track_recommendations


class TestGetTrackRecommendations:
    """Test suite for get_track_recommendations tool"""

    def test_get_track_recommendations_with_seed_tracks(self, config_with_spotify_client, mock_spotify_client):
        """Test recommendations with seed tracks"""
        # Arrange
        seed_tracks = ["track1", "track2"]
        limit = 10
        
        # Act
        result = get_track_recommendations.invoke(
            {"seed_tracks": seed_tracks, "limit": limit}, config_with_spotify_client
        )
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1  # Based on mock data
        
        track = result[0]
        assert track["id"] == "rec1"
        assert track["name"] == "Recommended Track 1"
        
        mock_spotify_client.recommendations.assert_called_once()

    def test_get_track_recommendations_with_audio_features(self, config_with_spotify_client, mock_spotify_client):
        """Test recommendations with audio features"""
        # Arrange
        seed_genres = ["pop"]
        target_energy = 0.8
        target_danceability = 0.7
        
        # Act
        result = get_track_recommendations.invoke({
            "seed_genres": seed_genres,
            "target_energy": target_energy,
            "target_danceability": target_danceability
        }, config_with_spotify_client)
        
        # Assert
        assert isinstance(result, list)
        mock_spotify_client.recommendations.assert_called_once()

    def test_get_track_recommendations_no_client(self, empty_config):
        """Test recommendations when no Spotify client is provided"""
        # Arrange
        seed_tracks = ["track1"]
        
        # Act
        result = get_track_recommendations.invoke({
            "seed_tracks": seed_tracks
        }, empty_config)
        
        # Assert
        assert result == []

    def test_get_track_recommendations_api_error(self, config_with_spotify_client, mock_spotify_client):
        """Test recommendations when API throws error"""
        # Arrange
        seed_tracks = ["error_track"]
        mock_spotify_client.recommendations.side_effect = Exception("API error")
        
        # Act
        result = get_track_recommendations.invoke({
            "seed_tracks": seed_tracks
        }, config_with_spotify_client)
        
        # Assert
        assert result == []