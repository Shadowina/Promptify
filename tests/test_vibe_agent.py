import pytest
import json
from unittest.mock import MagicMock
from vibe_agent import get_candidate_models, vibe_music_agent, GeneratedPlaylist

def test_get_candidate_models_excludes_retired_models(monkeypatch):
    """Verify get_candidate_models does not include retired Gemini 1.0, 1.5, 2.0, or 2.5 models."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")
    candidates = get_candidate_models()
    
    # Retired models must be filtered out
    assert "gemini-1.5-flash" not in candidates
    assert "gemini-pro" not in candidates
    assert "gemini-1.5-pro" not in candidates
    assert "gemini-2.0-flash" not in candidates
    assert "gemini-2.5-flash" not in candidates
    
    # Active models must be present
    assert "gemini-3.5-flash" in candidates
    assert "gemini-3.8-flash" in candidates

def test_vibe_music_agent_invokes_genai_client(monkeypatch):
    """Verify vibe_music_agent calls client.models.generate_content with structured config."""
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy_key")
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "name": "Rainy Drive",
        "description": "Late night chill tunes",
        "songs": [
            {"title": "Nightcall", "artist": "Kavinsky", "reason": "Moody synths"},
            {"title": "Resonance", "artist": "HOME", "reason": "Nostalgic vibe"}
        ]
    })
    mock_client.models.generate_content.return_value = mock_response
    
    result = vibe_music_agent("rainy drive", num_songs=2, genai_client=mock_client)
    
    assert mock_client.models.generate_content.called
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-3.5-flash"
    assert call_kwargs["config"].response_mime_type == "application/json"
    assert call_kwargs["config"].response_schema == GeneratedPlaylist
    
    # Verify result can be parsed
    parsed = json.loads(result)
    assert parsed["name"] == "Rainy Drive"
    assert len(parsed["songs"]) == 2

def test_vibe_music_agent_falls_back_on_model_not_found(monkeypatch):
    """Verify fallback mechanism tries second candidate if first model returns 404."""
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy_key")
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"name": "Fallback Playlist", "songs": []}'
    
    # First call raises 404 Not Found, second call succeeds
    mock_client.models.generate_content.side_effect = [
        Exception("404 Model not found"),
        mock_response
    ]
    
    result = vibe_music_agent("test vibe", genai_client=mock_client)
    assert mock_client.models.generate_content.call_count == 2
    assert "Fallback Playlist" in result
