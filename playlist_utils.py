import spotipy
from spotipy.oauth2 import SpotifyOAuth
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
SPOTIPY_REDIRECT_URI = "http://localhost:8501"
TOKEN_CACHE = ".spotify_token_cache"

# Rate limiting configuration
SEARCH_DELAY = 1.0  # Increased from 0.5 to 1.0 seconds between searches
BATCH_DELAY = 2.0   # Increased from 1.0 to 2.0 seconds between batch additions
MAX_RETRIES = 5     # Increased from 3 to 5 retries
BATCH_SIZE = 10     # Reduced from 20 to 10 tracks per batch

# Global Spotify client
_spotify_client = None

def get_spotify_client():
    global _spotify_client
    
    # If we already have a client, return it
    if _spotify_client is not None:
        return _spotify_client

    # Try to load cached token
    try:
        with open(TOKEN_CACHE, 'r') as f:
            token_info = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        token_info = None

    # Initialize OAuth
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="playlist-modify-public",
        cache_path=TOKEN_CACHE
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
                        _spotify_client = spotipy.Spotify(auth=access_token)
                        return _spotify_client
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
            _spotify_client = spotipy.Spotify(auth=access_token)
            return _spotify_client
            
        except Exception as e:
            st.error(f"Error during authentication: {str(e)}")
            return None

    # If we don't have a code, show the authorization link
    auth_url = sp_oauth.get_authorize_url()
    st.markdown("### Spotify Authentication Required")
    st.markdown("Please click the link below to authorize the app:")
    st.markdown(f"[Authorize with Spotify]({auth_url})")
    
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

def save_playlist_to_spotify(playlist_name, playlist_result):
    """Save a playlist to Spotify with proper rate limiting and error handling"""
    try:
        # Get the Spotify client
        sp = get_spotify_client()
        if sp is None:
            raise Exception("Failed to initialize Spotify client")

        # Parse the playlist result to extract track names and artists
        track_entries = []
        for line in playlist_result.split('\n'):
            if line.strip() and line[0].isdigit():  # Lines starting with numbers are track entries
                # Extract track name and artist
                parts = line.split(' by ')
                if len(parts) == 2:
                    track_name = parts[0].split('. ', 1)[1].strip()  # Remove the number and dot
                    artist = parts[1].strip()
                    track_entries.append((track_name, artist))

        if not track_entries:
            raise Exception("No valid tracks found in the playlist result")

        st.info(f"Found {len(track_entries)} tracks to add to the playlist")

        # Get user ID
        user_info = safe_spotify_request(sp.current_user)
        user_id = user_info['id']
        st.info("Successfully got user ID")

        # Create playlist
        playlist = safe_spotify_request(
            sp.user_playlist_create,
            user=user_id,
            name=playlist_name,
            public=True
        )
        st.info("Playlist created successfully")

        # Search for tracks with rate limiting
        track_uris = []
        progress_bar = st.progress(0)
        total_tracks = len(track_entries)

        for i, (track_name, artist) in enumerate(track_entries, 1):
            try:
                # Update progress
                progress_bar.progress(i / total_tracks)
                st.info(f"Searching for track {i}/{total_tracks}: {track_name} by {artist}")

                # Search with both track name and artist
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
                    st.success(f"Found: {track_name} by {artist}")
                else:
                    st.warning(f"Could not find track: {track_name} by {artist}")

                # Add delay between searches
                time.sleep(SEARCH_DELAY)

            except Exception as e:
                st.error(f"Error searching for track '{track_name}': {str(e)}")
                continue

        st.info(f"Found {len(track_uris)} tracks out of {total_tracks} requested")

        # Add tracks in batches with rate limiting
        if track_uris:
            st.info(f"Adding tracks in batches of {BATCH_SIZE}...")
            
            for i in range(0, len(track_uris), BATCH_SIZE):
                batch = track_uris[i:i + BATCH_SIZE]
                st.info(f"Adding batch {i//BATCH_SIZE + 1} ({len(batch)} tracks)...")
                
                try:
                    safe_spotify_request(
                        sp.user_playlist_add_tracks,
                        user=user_id,
                        playlist_id=playlist['id'],
                        tracks=batch
                    )
                    #st.success(f"Successfully added batch {i//BATCH_SIZE + 1}")
                    
                    # Add delay between batches
                    time.sleep(BATCH_DELAY)
                    
                except Exception as e:
                    st.error(f"Error adding batch: {str(e)}")
                    continue

            st.success("All tracks added successfully!")
        else:
            st.warning("No tracks were found to add to the playlist")

        playlist_url = playlist['external_urls']['spotify']
        st.success(f"Playlist created successfully! URL: {playlist_url}")
        return playlist_url

    except Exception as e:
        st.error(f"Error creating playlist: {str(e)}")
        raise
        
    
