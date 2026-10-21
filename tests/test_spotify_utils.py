import pytest
from unittest.mock import MagicMock
from playlist_utils import extract_track_entries, save_playlist_to_spotify, get_playlist_preview_data

def test_extract_track_entries_from_dict():
    """Verify extracting track entries from parsed dictionary."""
    data = {
        "name": "Lo-Fi Beats",
        "songs": [
            {"title": "Coffee Breath", "artist": "Sofia Mills"},
            {"title": '"Get You The Moon"', "artist": "'Kina'"}
        ]
    }
    extracted = extract_track_entries(data)
    assert extracted == [("Coffee Breath", "Sofia Mills"), ("Get You The Moon", "Kina")]

def test_extract_track_entries_from_tuples_list():
    """Verify extracting track entries from list of tuples."""
    data = [("Song A", "Artist A"), ("Song B", "Artist B")]
    extracted = extract_track_entries(data)
    assert extracted == [("Song A", "Artist A"), ("Song B", "Artist B")]

def test_extract_track_entries_from_legacy_string():
    """Verify extracting track entries from plain string format."""
    text = "1. Song One by Artist One\n2. Song Two by Artist Two - Great vibe"
    extracted = extract_track_entries(text)
    assert extracted == [("Song One", "Artist One"), ("Song Two", "Artist Two")]

def test_get_playlist_preview_data_unauthenticated_returns_empty(monkeypatch):
    """Verify get_playlist_preview_data safely returns empty list if unauthenticated."""
    monkeypatch.setattr("playlist_utils.get_spotify_client", lambda: None)
    result = get_playlist_preview_data({"songs": [{"title": "Song", "artist": "Artist"}]}, sp=None)
    assert result == []

def test_save_playlist_to_spotify_uses_modern_endpoints():
    """Verify save_playlist_to_spotify calls current_user_playlist_create and playlist_add_items."""
    mock_sp = MagicMock()
    
    # Mock current_user_playlist_create
    mock_sp.current_user_playlist_create.return_value = {
        "id": "playlist_123",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_123"}
    }
    
    # Mock search
    mock_sp.search.return_value = {
        "tracks": {
            "items": [{"uri": "spotify:track:abc123"}]
        }
    }
    
    # Mock playlist_add_items
    mock_sp.playlist_add_items.return_value = {"snapshot_id": "snap_123"}
    
    songs_data = {
        "name": "Dream Pop",
        "songs": [
            {"title": "Space Song", "artist": "Beach House"}
        ]
    }
    
    url = save_playlist_to_spotify("Dream Pop", songs_data, sp=mock_sp)
    
    # Verify modern endpoint calls
    mock_sp.current_user_playlist_create.assert_called_once_with(
        name="Dream Pop",
        public=True,
        description="Curated with Promptify AI"
    )
    
    # Verify search was called with exact query
    mock_sp.search.assert_called_once_with(
        q="track:Space Song artist:Beach House",
        type="track",
        limit=1
    )
    
    # Verify playlist_add_items was called instead of deprecated user_playlist_add_tracks
    mock_sp.playlist_add_items.assert_called_once_with(
        playlist_id="playlist_123",
        items=["spotify:track:abc123"]
    )
    
    assert url == "https://open.spotify.com/playlist/playlist_123"

def test_save_playlist_to_spotify_with_user_playlist_create():
    """Verify save_playlist_to_spotify works with standard spotipy user_playlist_create."""
    mock_sp = MagicMock(spec=["user_playlist_create", "current_user", "search", "playlist_add_items"])
    mock_sp.current_user.return_value = {"id": "spotify_user_456"}
    mock_sp.user_playlist_create.return_value = {
        "id": "playlist_456",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_456"}
    }
    mock_sp.search.return_value = {
        "tracks": {"items": [{"uri": "spotify:track:xyz789"}]}
    }
    mock_sp.playlist_add_items.return_value = {"snapshot_id": "snap_456"}

    url = save_playlist_to_spotify(
        "Indie Chill",
        {"songs": [{"title": "Song A", "artist": "Artist B"}]},
        sp=mock_sp
    )

    mock_sp.current_user.assert_called_once()
    mock_sp.user_playlist_create.assert_called_once_with(
        user="spotify_user_456",
        name="Indie Chill",
        public=True,
        description="Curated with Promptify AI"
    )
    assert url == "https://open.spotify.com/playlist/playlist_456"
