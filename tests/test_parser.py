import pytest
from app import parse_playlist, convert_playlist_to_text

SAMPLE_PLAYLIST_TEXT = """## Late Night Chill Vibes

A relaxed playlist for late evening focus and calming vibes.

1. Midnight City by M83
- Dreamy synth-pop with an iconic saxophone riff
2. Sunset Lover by Petit Biscuit
- Warm, soothing electronic melody
3. Nightcall by Kavinsky
- Dark, moody electronic soundscape
"""

def test_parse_playlist_extracts_name_and_songs():
    """Verify parse_playlist extracts the playlist name and song entries."""
    parsed = parse_playlist(SAMPLE_PLAYLIST_TEXT)
    assert parsed["name"] == "Late Night Chill Vibes"
    assert len(parsed["songs"]) == 3
    
    assert parsed["songs"][0]["title"] == "Midnight City"
    assert parsed["songs"][0]["artist"] == "M83"
    assert parsed["songs"][0]["number"] == "1"

    assert parsed["songs"][1]["title"] == "Sunset Lover"
    assert parsed["songs"][1]["artist"] == "Petit Biscuit"
    assert parsed["songs"][1]["number"] == "2"

    assert parsed["songs"][2]["title"] == "Nightcall"
    assert parsed["songs"][2]["artist"] == "Kavinsky"
    assert parsed["songs"][2]["number"] == "3"

def test_parse_playlist_empty_string():
    """Verify parse_playlist handles empty input safely."""
    parsed = parse_playlist("")
    assert parsed["name"] == ""
    assert parsed["songs"] == []

def test_convert_playlist_to_text_roundtrip():
    """Verify convert_playlist_to_text creates valid text from parsed structure."""
    parsed = {
        "name": "Summer Nostalgia",
        "songs": [
            {"number": "1", "title": "Cruel Summer", "artist": "Taylor Swift"},
            {"number": "2", "title": "Golden Hour", "artist": "JVKE"}
        ]
    }
    text = convert_playlist_to_text(parsed)
    assert "## Summer Nostalgia" in text
    assert "1. Cruel Summer by Taylor Swift" in text
    assert "2. Golden Hour by JVKE" in text

def test_parse_playlist_from_json_string():
    """Verify parse_playlist parses valid JSON output from structured model."""
    json_str = '{"name": "Synthwave Sunset", "description": "Retro drive", "songs": [{"title": "Sunset", "artist": "The Midnight", "reason": "Retro"}]}'
    parsed = parse_playlist(json_str)
    assert parsed["name"] == "Synthwave Sunset"
    assert parsed["description"] == "Retro drive"
    assert len(parsed["songs"]) == 1
    assert parsed["songs"][0]["title"] == "Sunset"
    assert parsed["songs"][0]["artist"] == "The Midnight"
    assert parsed["songs"][0]["number"] == "1"

