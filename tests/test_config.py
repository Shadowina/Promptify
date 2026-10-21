import os
import pytest
from pathlib import Path

def test_vibe_agent_import_without_google_api_key(monkeypatch):
    """Ensure importing or reloading vibe_agent without GOOGLE_API_KEY does not raise an exception."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    import vibe_agent
    assert hasattr(vibe_agent, "get_google_api_key")

def test_get_google_api_key_raises_when_missing(monkeypatch):
    """Ensure get_google_api_key raises a descriptive ValueError when GOOGLE_API_KEY is not set."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from vibe_agent import get_google_api_key
    with pytest.raises(ValueError, match="GOOGLE_API_KEY environment variable is not set"):
        get_google_api_key()

def test_get_google_api_key_returns_key(monkeypatch):
    """Ensure get_google_api_key returns the key when present in the environment."""
    test_key = "test_key_xyz_123"
    monkeypatch.setenv("GOOGLE_API_KEY", test_key)
    from vibe_agent import get_google_api_key
    assert get_google_api_key() == test_key

def test_env_example_contains_required_keys():
    """Verify that .env.example exists and contains all required configuration keys."""
    env_example_path = Path(__file__).resolve().parent.parent / ".env.example"
    assert env_example_path.exists(), ".env.example must exist"
    
    content = env_example_path.read_text(encoding="utf-8")
    required_keys = [
        "GOOGLE_API_KEY",
        "GEMINI_MODEL",
        "SPOTIPY_CLIENT_ID",
        "SPOTIPY_CLIENT_SECRET",
        "SPOTIPY_REDIRECT_URI",
    ]
    for key in required_keys:
        assert key in content, f"Key '{key}' missing from .env.example"
