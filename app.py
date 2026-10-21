import streamlit as st
import os
import re
from vibe_agent import vibe_music_agent
from playlist_utils import save_playlist_to_spotify, get_spotify_client, get_playlist_preview_data

import json

def parse_playlist(playlist_input):
    """Parse playlist into structured format, supporting dicts, JSON strings, and markdown."""
    if isinstance(playlist_input, dict):
        return playlist_input
    
    if not playlist_input or not isinstance(playlist_input, str):
        return {'name': '', 'songs': []}

    # Try parsing as JSON object (e.g. from structured model outputs)
    try:
        data = json.loads(playlist_input)
        if isinstance(data, dict) and "songs" in data:
            songs = []
            for i, s in enumerate(data.get("songs", []), 1):
                if isinstance(s, dict):
                    title = s.get("title", "").strip().strip('"\'')
                    artist = s.get("artist", "").strip().strip('"\'')
                    songs.append({
                        'number': str(i),
                        'title': title,
                        'artist': artist,
                        'line': f"{i}. {title} by {artist}"
                    })
            return {
                'name': data.get("name", "").strip(),
                'description': data.get("description", "").strip(),
                'songs': songs
            }
    except (json.JSONDecodeError, ValueError):
        pass

    # Markdown line-by-line fallback parsing
    lines = playlist_input.split('\n')
    playlist_name = ""
    songs = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('##'):
            playlist_name = line.replace('##', '').strip()
        elif line and (re.match(r'^\d+[\.\)]\s*', line) or line.startswith('- ') or line.startswith('* ')):
            # Clean leading numbers or list bullets
            cleaned_line = re.sub(r'^\d+[\.\)]\s*', '', line)
            cleaned_line = re.sub(r'^[-*]\s*', '', cleaned_line)
            
            if ' by ' in cleaned_line:
                parts = cleaned_line.split(' by ', 1)
                song_title = parts[0].strip().strip('"\'')
                # Remove trailing reason if attached on same line via dash
                artist_raw = parts[1].split(' - ', 1)[0].strip().strip('"\'')
                artist = artist_raw.split(' – ', 1)[0].strip()
                
                num_match = re.match(r'^(\d+)', line)
                song_num = num_match.group(1) if num_match else str(len(songs) + 1)
                
                songs.append({
                    'number': song_num,
                    'title': song_title,
                    'artist': artist,
                    'line': f"{song_num}. {song_title} by {artist}"
                })
    
    return {
        'name': playlist_name,
        'songs': songs
    }


def convert_playlist_to_text(parsed_playlist):
    """Convert parsed playlist back to text format for export or display."""
    lines = []
    if parsed_playlist.get('name'):
        lines.append(f"## {parsed_playlist['name']}")
        lines.append("")
    
    for song in parsed_playlist.get('songs', []):
        lines.append(f"{song['number']}. {song['title']} by {song['artist']}")
    
    return "\n".join(lines)

# Page config
st.set_page_config(
    page_title="Promptify",
    page_icon="🎵",
    layout="centered"
)

# Custom CSS for styling
st.markdown("""
<style>
    .theme-toggle {
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 1000;
    }
    .stButton > button {
        border-radius: 20px;
        padding: 0.5rem 1rem;
    }
    .playlist-item {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .playlist-item:hover {
        background-color: #f0f0f0;
    }
</style>
""", unsafe_allow_html=True)

# Theme toggle and Spotify status in sidebar
with st.sidebar:
    st.title("🎛️ Settings")
    theme = st.selectbox(
        "Theme",
        ["Light", "Dark"],
        index=0,
        help="Choose your preferred theme"
    )
    
    if theme == "Dark":
        st.markdown("""
        <style>
        .stApp {
            background-color: #1a1a1a;
            color: #ffffff;
        }
        .stTextInput > div > div > input {
            background-color: #2d2d2d;
            color: #ffffff;
            border-color: #404040;
        }
        .stSelectbox > div > div > select {
            background-color: #2d2d2d;
            color: #ffffff;
        }
        </style>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("🎵 Spotify Status")
    spotify_configured = bool(os.getenv("SPOTIPY_CLIENT_ID") and os.getenv("SPOTIPY_CLIENT_SECRET"))
    if not spotify_configured:
        st.warning("Spotify credentials not set in .env. You can generate playlists, but Spotify saving is disabled.")
    else:
        if 'spotify_client' not in st.session_state:
            st.session_state.spotify_client = None
        
        # Check if auth callback or token exists
        if st.session_state.spotify_client is None:
            st.session_state.spotify_client = get_spotify_client()
        
        if st.session_state.spotify_client is not None:
            st.success("✅ Spotify Connected")
        else:
            st.info("Spotify not connected. You can still generate playlists, and connect when ready to save.")

# Header
st.title("🎵 Promptify")
st.markdown("### Your AI-Powered Playlist Generator")

# Main content
st.divider()
st.subheader("🎯 Enter Your Vibe")
st.markdown("Describe your mood, feelings, or the vibe you want in your playlist:")

# Vibe input with validation
vibe_input = st.text_input(
    label="Vibe description",
    value="late night heartbreak under the rain 🌧️",
    placeholder="e.g., late night drive through Tokyo neon rain...",
    label_visibility="collapsed"
)

# Playlist length input
playlist_length = st.number_input(
    label="Number of songs in playlist",
    min_value=5,
    max_value=50,
    value=15,
    step=1,
    help="Choose how many songs you want in your playlist."
)

# Generate button
if st.button("Generate Playlist", type="primary", use_container_width=True):
    cleaned_vibe = vibe_input.strip() if vibe_input else ""
    if not cleaned_vibe:
        st.error("Please enter a vibe or mood!")
    elif len(cleaned_vibe) < 3:
        st.error("Please enter a more descriptive vibe (at least 3 characters).")
    elif len(cleaned_vibe) > 500:
        st.error("Vibe description is too long (maximum 500 characters).")
    else:
        with st.spinner("🎵 Generating your perfect playlist..."):
            try:
                result = vibe_music_agent(cleaned_vibe, num_songs=playlist_length)
                st.session_state["playlist_result"] = result
                st.session_state["playlist_name"] = f"Vibe - {cleaned_vibe}"
                # Store structured parsed playlist directly
                st.session_state["parsed_playlist"] = parse_playlist(result)
                # Clear old preview data
                if "preview_data" in st.session_state:
                    del st.session_state["preview_data"]
                st.success("🎉 Playlist generated successfully!")
            except Exception as e:
                st.error(f"❌ Error generating playlist: {str(e)}")

# Display playlist result
if "playlist_result" in st.session_state:
    st.divider()
    st.subheader("🎧 Your Generated Playlist")
    playlist_result = st.session_state["playlist_result"]
    
    # Ensure parsed playlist exists
    if "parsed_playlist" not in st.session_state:
        st.session_state.parsed_playlist = parse_playlist(playlist_result)
    
    # Load preview data if Spotify is connected
    if "preview_data" not in st.session_state:
        sp = st.session_state.get("spotify_client")
        if sp is not None:
            with st.spinner("🎵 Loading song details and album art..."):
                st.session_state.preview_data = get_playlist_preview_data(st.session_state.parsed_playlist, sp=sp)
        else:
            st.session_state.preview_data = []
    
    # Playlist preview and editing
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Playlist Preview")
        parsed = st.session_state.parsed_playlist
        preview_data = st.session_state.get("preview_data", [])
        
        if parsed.get('name'):
            st.markdown(f"**Playlist Name:** {parsed['name']}")
        
        # Display songs with enhanced preview if available
        for i, song in enumerate(parsed.get('songs', [])):
            with st.container():
                song_preview = None
                for preview in preview_data:
                    if (preview.get('title', '').lower() == song['title'].lower() and 
                        preview.get('artist', '').lower() == song['artist'].lower()):
                        song_preview = preview
                        break
                
                col_art, col_song, col_remove = st.columns([1, 3, 1])
                
                with col_art:
                    if song_preview and song_preview.get('details') and song_preview['details'].get('album_art'):
                        st.image(song_preview['details']['album_art'], width=50)
                    else:
                        st.markdown("🎵")
                
                with col_song:
                    album_text = ""
                    if song_preview and song_preview.get('details') and song_preview['details'].get('album_name'):
                        album_text = f"<br><small>Album: {song_preview['details']['album_name']}</small>"
                    st.markdown(f"""
                    <div class="playlist-item">
                        <strong>{song['number']}. {song['title']}</strong><br>
                        <em>by {song['artist']}</em>
                        {album_text}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_remove:
                    if st.button("🗑️", key=f"remove_{i}", help="Remove this song"):
                        parsed['songs'].pop(i)
                        if song_preview and song_preview in preview_data:
                            preview_data.remove(song_preview)
                        st.rerun()
    
    with col2:
        st.markdown("### Edit Playlist")
        
        # Add new song
        st.markdown("**Add a song:**")
        new_title = st.text_input("Song title", key="new_title", placeholder="Enter song title")
        new_artist = st.text_input("Artist", key="new_artist", placeholder="Enter artist name")
        
        if st.button("➕ Add Song", key="add_song"):
            if new_title and new_artist:
                new_song = {
                    'number': str(len(parsed['songs']) + 1),
                    'title': new_title.strip(),
                    'artist': new_artist.strip(),
                    'line': f"{len(parsed['songs']) + 1}. {new_title.strip()} by {new_artist.strip()}"
                }
                parsed['songs'].append(new_song)
                
                sp = st.session_state.get("spotify_client")
                if sp:
                    from playlist_utils import search_song_details
                    details = search_song_details(sp, new_title.strip(), new_artist.strip())
                    new_preview = {
                        'title': new_title.strip(),
                        'artist': new_artist.strip(),
                        'details': details
                    }
                    preview_data.append(new_preview)
                
                st.rerun()
        
        st.divider()
        
        # Playlist stats
        st.markdown("**Playlist Stats:**")
        st.markdown(f"• **Total songs:** {len(parsed['songs'])}")
        st.markdown(f"• **Duration:** ~{len(parsed['songs']) * 3.5:.0f} minutes")
        
        # Regenerate button
        if st.button("🔄 Regenerate", key="regenerate"):
            del st.session_state["playlist_result"]
            if "parsed_playlist" in st.session_state:
                del st.session_state["parsed_playlist"]
            if "preview_data" in st.session_state:
                del st.session_state["preview_data"]
            st.rerun()
    
    # Display original playlist in an expander
    with st.expander("View Original Text", expanded=False):
        st.write(playlist_result)

    # Save to Spotify button
    if st.button("💾 Save to Spotify", type="primary", use_container_width=True):
        sp = st.session_state.get("spotify_client")
        if sp is None:
            sp = get_spotify_client()
            if sp is not None:
                st.session_state.spotify_client = sp

        if sp is None:
            st.warning("⚠️ Spotify connection required to save playlists. Please click the authorization link in the sidebar or above to connect your account.")
        else:
            with st.spinner("📤 Saving your playlist to Spotify..."):
                try:
                    playlist_url = save_playlist_to_spotify(
                        st.session_state["playlist_name"],
                        st.session_state.parsed_playlist,
                        sp=sp
                    )
                    st.success(f"✅ Playlist saved to Spotify successfully! [Open on Spotify]({playlist_url})")
                except Exception as e:
                    st.error(f"❌ Failed to save playlist: {str(e)}")

# Footer
st.divider()
st.markdown("Made with ❤️ using Spotify API and GEMINI AI")
