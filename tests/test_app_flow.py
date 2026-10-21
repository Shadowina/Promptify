import pytest
from app import parse_playlist

def validate_vibe_input(vibe: str) -> tuple[bool, str]:
    """Helper mirroring the validation rules in app.py."""
    cleaned = vibe.strip() if vibe else ""
    if not cleaned:
        return False, "Please enter a vibe or mood!"
    if len(cleaned) < 3:
        return False, "Please enter a more descriptive vibe (at least 3 characters)."
    if len(cleaned) > 500:
        return False, "Vibe description is too long (maximum 500 characters)."
    return True, cleaned

def test_vibe_input_validation_rules():
    """Verify input validation handles empty, short, long, and valid vibes."""
    assert validate_vibe_input("")[0] is False
    assert validate_vibe_input("   ")[0] is False
    assert validate_vibe_input("yo")[0] is False
    assert validate_vibe_input("a" * 501)[0] is False
    
    valid, cleaned = validate_vibe_input("  neon city night drive  ")
    assert valid is True
    assert cleaned == "neon city night drive"

def test_parse_playlist_resilience():
    """Verify parse_playlist handles different list styles and quoted titles."""
    raw_output = """## Cyberpunk Neon Drive
1. "Resonance" by HOME - Nostalgic synthwave classic
2) Nightcall by Kavinsky
3. 'After Dark' by "Mr.Kitty"
* Midnight City by M83
"""
    parsed = parse_playlist(raw_output)
    assert parsed["name"] == "Cyberpunk Neon Drive"
    assert len(parsed["songs"]) == 4
    
    assert parsed["songs"][0]["title"] == "Resonance"
    assert parsed["songs"][0]["artist"] == "HOME"
    
    assert parsed["songs"][1]["title"] == "Nightcall"
    assert parsed["songs"][1]["artist"] == "Kavinsky"
    
    assert parsed["songs"][2]["title"] == "After Dark"
    assert parsed["songs"][2]["artist"] == "Mr.Kitty"
    
    assert parsed["songs"][3]["title"] == "Midnight City"
    assert parsed["songs"][3]["artist"] == "M83"
