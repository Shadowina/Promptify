import streamlit as st
from vibe_agent import vibe_music_agent
from playlist_utils import save_playlist_to_spotify, get_spotify_client
import os

# Page config
st.set_page_config(
    page_title="Promptify",
    page_icon="🎵",
    layout="centered"
)

# Header
st.title("🎵 Promptify")
st.markdown("### Your AI-Powered Playlist Generator")

# Authentication section
st.divider()
st.subheader("🔐 Authentication")
if not os.getenv("SPOTIPY_CLIENT_ID") or not os.getenv("SPOTIPY_CLIENT_SECRET"):
    st.error("Please set your Spotify credentials in the .env file!")
    st.stop()

# Initialize Spotify client
if 'spotify_client' not in st.session_state:
    st.session_state.spotify_client = None

# Try to initialize Spotify client
if st.session_state.spotify_client is None:
    st.session_state.spotify_client = get_spotify_client()

# If we're still not authenticated, show the auth message and stop
if st.session_state.spotify_client is None:
    st.warning("Please click the 'Authorize with Spotify' link above to continue.")
    st.stop()

# Main content
st.divider()
st.subheader("🎯 Enter Your Vibe")
st.markdown("Describe your mood, feelings, or the vibe you want in your playlist:")

# Vibe input
vibe_input = st.text_input(
    label="Vibe description",
    value="late night heartbreak under the rain 🌧️",
    placeholder="Enter your vibe here...",
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
if st.button("✨ Generate Playlist", type="primary", use_container_width=True):
    if not vibe_input:
        st.error("Please enter a vibe or mood!")
    else:
        with st.spinner("🎵 Generating your perfect playlist..."):
            try:
                result = vibe_music_agent(vibe_input, num_songs=playlist_length)
                st.session_state["playlist_result"] = result
                st.success("🎉 Playlist generated successfully!")
            except Exception as e:
                st.error(f"❌ Error generating playlist: {str(e)}")

# Display playlist result
if "playlist_result" in st.session_state:
    st.divider()
    st.subheader("🎧 Your Generated Playlist")
    playlist_result = st.session_state["playlist_result"]
    
    # Display playlist in an expander
    with st.expander("View Playlist", expanded=True):
        st.write(playlist_result)

    # Save to Spotify button
    if st.button("💾 Save to Spotify", type="primary", use_container_width=True):
        with st.spinner("📤 Saving your playlist to Spotify..."):
            try:
                save_playlist_to_spotify("Vibe - Custom Playlist", playlist_result)
                st.success("✅ Playlist saved to Spotify successfully!")
            except Exception as e:
                st.error(f"❌ Failed to save playlist: {str(e)}")

# Footer
st.divider()
st.markdown("Made with ❤️ using Spotify API and GEMINI AI")


