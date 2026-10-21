import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler
import os
import json
from dotenv import load_dotenv
import webbrowser
import time
from spotipy.exceptions import SpotifyException
import streamlit as st
from urllib.parse import urlparse, parse_qs

load_dotenv()

# Configure Spotify
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
# Redirect URI must match exactly what's registered in Spotify Developer Dashboard
# IMPORTANT: According to Spotify docs, 'localhost' is NOT allowed - must use explicit IP like 127.0.0.1
# See: https://developer.spotify.com/documentation/web-api/concepts/redirect_uri
# You can override this by setting SPOTIPY_REDIRECT_URI in your .env file
# For loopback addresses, use: http://127.0.0.1:8501 or http://[::1]:8501 (IPv6)
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8501")
TOKEN_CACHE = ".spotify_token_cache"

# Rate limiting configuration
SEARCH_DELAY = 0.05  # Light delay between searches; relies on Spotify 429 Retry-After for backoff
BATCH_DELAY = 0.5    # Brief delay between batch additions
MAX_RETRIES = 5      # Maximum retries on 429 rate limit
BATCH_SIZE = 10      # 10 tracks per batch

def get_spotify_client():
    """Retrieve or initialize the Spotify client isolated to the active Streamlit session."""
    try:
        if hasattr(st, "session_state") and st.session_state.get("spotify_client") is not None:
            return st.session_state.spotify_client
    except Exception:
        pass

    # Try to load cached token
    try:
        with open(TOKEN_CACHE, 'r') as f:
            token_info = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        token_info = None

    # Initialize OAuth with explicit cache handler and public + private playlist scopes
    cache_handler = CacheFileHandler(cache_path=TOKEN_CACHE)
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="playlist-modify-public playlist-modify-private",
        cache_handler=cache_handler
    )

    # Get or refresh token
    if token_info:
        try:
            # Check if token is expired
            if 'expires_at' in token_info:
                expires_at = token_info['expires_at']
                if isinstance(expires_at, str):
                    expires_at = float(expires_at)
                if time.time() < expires_at:
                    access_token = token_info.get('access_token')
                    if access_token:
                        client = spotipy.Spotify(auth=access_token)
                        try:
                            if hasattr(st, "session_state"):
                                st.session_state.spotify_client = client
                        except Exception:
                            pass
                        return client
        except Exception:
            pass  # If there's any error, we'll get a new token

    # Check if we have a code in the URL
    query_params = st.query_params
    if 'code' in query_params:
        code = query_params['code']
        try:
            # Clear the code from the URL
            st.query_params.clear()
            
            token_info = sp_oauth.get_access_token(code)
            if not token_info:
                st.error("Failed to get access token. Please try again.")
                return None
                
            # Save the token info to cache
            with open(TOKEN_CACHE, 'w') as f:
                json.dump(token_info, f)
                
            access_token = token_info.get('access_token')
            if not access_token:
                st.error("No access token in response. Please try again.")
                return None
                
            st.success("Successfully authenticated with Spotify!")
            client = spotipy.Spotify(auth=access_token)
            try:
                if hasattr(st, "session_state"):
                    st.session_state.spotify_client = client
            except Exception:
                pass
            return client
            
        except Exception as e:
            st.error(f"Error during authentication: {str(e)}")
            return None

    # If we don't have a code, show the authorization link
    auth_url = sp_oauth.get_authorize_url()
    st.markdown("### Spotify Authentication Required")
    st.markdown("Please click the link below to authorize the app:")
    st.markdown(f"[Authorize with Spotify]({auth_url})")
    
    # Show helpful information about redirect URI
    st.info(f"""
    **Important:** Make sure this redirect URI is registered in your Spotify Developer Dashboard:
    
    `{SPOTIPY_REDIRECT_URI}`
    
    If you're getting an "INVALID_CLIENT: Insecure redirect URI" error:
    1. Go to https://developer.spotify.com/dashboard
    2. Select your app
    3. Click "Edit Settings"
    4. Under "Redirect URIs", add exactly: `{SPOTIPY_REDIRECT_URI}`
    5. Click "Add" and then "Save"
    6. Try authorizing again
    
    **Note:** According to Spotify's documentation, `localhost` is NOT allowed. 
    You must use explicit IP addresses like `http://127.0.0.1:8501` (IPv4) or `http://[::1]:8501` (IPv6).
    See: https://developer.spotify.com/documentation/web-api/concepts/redirect_uri
    """)
    
    return None

def safe_spotify_request(func, *args, **kwargs):
    """Helper function to handle rate limiting and retries"""
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:  # Rate limit error
                retry_after = int(e.headers.get('Retry-After', 10))  # Default to 10 seconds if no Retry-After header
                st.warning(f"Rate limited. Waiting {retry_after} seconds before retrying...")
                time.sleep(retry_after)
            else:
                raise
    raise Exception("Max retries exceeded")

def extract_track_entries(playlist_data):
    """Normalize playlist data from dict, list, or text into a list of (title, artist) tuples."""
    track_entries = []
    if isinstance(playlist_data, dict) and "songs" in playlist_data:
        for s in playlist_data["songs"]:
            if isinstance(s, dict) and "title" in s and "artist" in s:
                track_entries.append((s["title"].strip('"\' '), s["artist"].strip('"\' ')))
    elif isinstance(playlist_data, list):
        for item in playlist_data:
            if isinstance(item, dict):
                track_entries.append((item.get("title", "").strip('"\' '), item.get("artist", "").strip('"\' ')))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                track_entries.append((str(item[0]).strip('"\' '), str(item[1]).strip('"\' ')))
    elif isinstance(playlist_data, str):
        for line in playlist_data.split('\n'):
            line = line.strip()
            if line and line[0].isdigit() and ' by ' in line:
                parts = line.split(' by ')
                if len(parts) == 2:
                    raw_title = parts[0]
                    track_name = raw_title.split('. ', 1)[1] if '. ' in raw_title else raw_title.split(' ', 1)[1]
                    artist = parts[1].split(' - ')[0].strip()
                    track_entries.append((track_name.strip('"\' '), artist.strip('"\' ')))
    return track_entries

def save_playlist_to_spotify(playlist_name, playlist_data, sp=None):
    """Save a playlist to Spotify using current Web API endpoints (POST /v1/me/playlists).
    
    Accepts playlist_data as a parsed dict, a track list, or legacy text.
    """
    try:
        if sp is None:
            sp = get_spotify_client()
        if sp is None:
            raise Exception("Spotify client is not authenticated. Please authorize with Spotify first.")

        track_entries = extract_track_entries(playlist_data)
        if not track_entries:
            raise Exception("No valid tracks found to add to the playlist.")

        st.info(f"Found {len(track_entries)} tracks to add to the playlist")

        # Create playlist using spotipy (supporting user_playlist_create with current_user or direct endpoint)
        if hasattr(sp, "current_user_playlist_create"):
            playlist = safe_spotify_request(
                sp.current_user_playlist_create,
                name=playlist_name,
                public=True,
                description="Curated with Promptify AI"
            )
        elif hasattr(sp, "user_playlist_create"):
            user_info = safe_spotify_request(sp.current_user)
            user_id = user_info.get("id") if isinstance(user_info, dict) else user_info
            playlist = safe_spotify_request(
                sp.user_playlist_create,
                user=user_id,
                name=playlist_name,
                public=True,
                description="Curated with Promptify AI"
            )
        else:
            payload = {
                "name": playlist_name,
                "public": True,
                "description": "Curated with Promptify AI"
            }
            playlist = safe_spotify_request(sp._post, "me/playlists", payload=payload)
        st.info("Playlist created successfully on Spotify")

        # Search for tracks
        track_uris = []
        progress_bar = st.progress(0)
        total_tracks = len(track_entries)

        for i, (track_name, artist) in enumerate(track_entries, 1):
            try:
                progress_bar.progress(i / total_tracks)
                st.info(f"Searching track {i}/{total_tracks}: {track_name} by {artist}")

                query = f"track:{track_name} artist:{artist}"
                results = safe_spotify_request(
                    sp.search,
                    q=query,
                    type="track",
                    limit=1
                )

                if results['tracks']['items']:
                    uri = results['tracks']['items'][0]['uri']
                    track_uris.append(uri)
                    st.success(f"Matched: {track_name} by {artist}")
                else:
                    st.warning(f"Could not find track: {track_name} by {artist}")

                if SEARCH_DELAY > 0:
                    time.sleep(SEARCH_DELAY)

            except Exception as e:
                st.error(f"Error searching for track '{track_name}': {str(e)}")
                continue

        st.info(f"Matched {len(track_uris)} of {total_tracks} requested tracks")

        # Add tracks in batches using current modern endpoint POST /v1/playlists/{id}/tracks
        if track_uris:
            st.info(f"Adding tracks in batches of {BATCH_SIZE}...")
            for i in range(0, len(track_uris), BATCH_SIZE):
                batch = track_uris[i:i + BATCH_SIZE]
                try:
                    safe_spotify_request(
                        sp.playlist_add_items,
                        playlist_id=playlist['id'],
                        items=batch
                    )
                    if BATCH_DELAY > 0:
                        time.sleep(BATCH_DELAY)
                except Exception as e:
                    st.error(f"Error adding batch: {str(e)}")
                    continue

            st.success("All matched tracks added successfully!")
        else:
            st.warning("No tracks were matched to add to the playlist")

        playlist_url = playlist['external_urls']['spotify']
        st.success(f"Playlist created successfully! URL: {playlist_url}")
        return playlist_url

    except Exception as e:
        st.error(f"Error creating playlist: {str(e)}")
        raise

def search_song_details(sp, track_name, artist_name):
    """Search for song details including album art and metadata."""
    try:
        query = f"track:{track_name} artist:{artist_name}"
        results = safe_spotify_request(
            sp.search,
            q=query,
            type="track",
            limit=1
        )
        
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            album_images = track['album'].get('images', [])
            return {
                'uri': track['uri'],
                'album_art': album_images[0]['url'] if album_images else None,
                'album_name': track['album']['name'],
                'duration_ms': track['duration_ms'],
                'popularity': track['popularity'],
                'preview_url': track.get('preview_url')
            }
        return None
    except Exception as e:
        st.warning(f"Could not fetch details for {track_name}: {str(e)}")
        return None

def get_playlist_preview_data(playlist_data, sp=None):
    """Get preview data for all songs in a playlist without blocking if unauthenticated."""
    if sp is None:
        sp = get_spotify_client()
    if sp is None:
        return []

    track_entries = extract_track_entries(playlist_data)
    preview_data = []
    for track_name, artist in track_entries:
        details = search_song_details(sp, track_name, artist)
        preview_data.append({
            'title': track_name,
            'artist': artist,
            'details': details
        })
    return preview_data

        
    
