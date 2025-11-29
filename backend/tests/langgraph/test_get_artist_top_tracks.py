"""
Comprehensive test suite for the get_artist_top_tracks tool
"""

import pytest
from app.langgraph_agent.tools import get_artist_top_tracks


class TestGetArtistTopTracks:
    """Test suite for get_artist_top_tracks tool"""

    def test_get_artist_top_tracks_successful(
        self, config_with_spotify_client, mock_spotify_client
    ):
        """Test successful retrieval of artist top tracks"""
        # Arrange
        artist_id = "test_artist_123"
        country = "US"

        # Act
        result = get_artist_top_tracks.invoke(
            {"artist_id": artist_id, "country": country}, config_with_spotify_client
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1  # Based on mock data

        track = result[0]
        assert track["id"] == "top1"
        assert track["name"] == "Top Track 1"
        assert track["artist"] == "Test Artist"
        assert track["uri"] == "spotify:track:top1"

        mock_spotify_client.artist_top_tracks.assert_called_once_with(
            artist_id, country=country
        )

    def test_get_artist_top_tracks_default_country(
        self, config_with_spotify_client, mock_spotify_client
    ):
        """Test get_artist_top_tracks with default country"""
        # Arrange
        artist_id = "test_artist_456"

        # Act
        result = get_artist_top_tracks.invoke(
            {"artist_id": artist_id}, config_with_spotify_client
        )

        # Assert
        assert isinstance(result, list)
        mock_spotify_client.artist_top_tracks.assert_called_once_with(
            artist_id, country="US"
        )

    def test_get_artist_top_tracks_no_spotify_client(self, empty_config):
        """Test get_artist_top_tracks when no Spotify client is provided"""
        # Arrange
        artist_id = "test_artist"

        # Act
        result = get_artist_top_tracks.invoke({"artist_id": artist_id}, empty_config)

        # Assert
        assert result == []

    def test_get_artist_top_tracks_api_error(
        self, config_with_spotify_client, mock_spotify_client
    ):
        """Test get_artist_top_tracks when Spotify API throws an error"""
        # Arrange
        artist_id = "error_artist"
        mock_spotify_client.artist_top_tracks.side_effect = Exception("API error")

        # Act
        result = get_artist_top_tracks.invoke(
            {"artist_id": artist_id}, config_with_spotify_client
        )

        # Assert
        assert result == []

    def test_get_artist_top_tracks_different_countries(
        self, config_with_spotify_client, mock_spotify_client
    ):
        """Test get_artist_top_tracks with different countries"""
        # Arrange
        artist_id = "global_artist"

        for country in ["US", "UK", "CA", "AU"]:
            # Act
            result = get_artist_top_tracks.invoke(
                {"artist_id": artist_id, "country": country}, config_with_spotify_client
            )

            # Assert
            assert isinstance(result, list)
