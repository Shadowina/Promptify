from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

texts = [
    "Now you are struggling to keep your eyes on the road",
    "Before the cool done run out",
    "I believe that the heart does go on (why does the heart go on?)",
    "Last Christmas, I gave you my heart",
    "All I want for Christmas is You",
    "Rudolf the red-nose reindeer",
    "If the world was ending, I wanna be next to you",
    "Meet me at the APT",
    "Can you meet me halfway",
    "Oh I live quite an impression",
    "Is this the real life? Is this just fantasy?",
    "Do you picture me, like i picture you?",
    "No need to ask, he's a smooth operator",
    "I can't make you love me",
    "How you like that",
    "Now every february, you'll be my valentine"
    "When you say you love me, know i love you more"
]



#initialize the embeddings and FAISS vector store

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vector_store = FAISS.from_texts(texts, embeddings)



#from google import genai
import google.generativeai as genai

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def vibe_music_agent(user_input, top_k=3, temperature=0.8, num_songs=15):
    #1. search for the most relevant songs
    similar_songs = vector_store.similarity_search(user_input, top_k=top_k, temperature=temperature)

    #RAG MODE
    if similar_songs:
        song_titles = [song.page_content for song in similar_songs]
        context = "\n".join(song_titles)
        prompt = f"""
        You are a music agent helping a user curate a playlist

User Vibe: {user_input}

Here are some similar vibes found in the database:
{context}

Based on the vibe and related examples above, create:
1. A creative playlist name that captures the essence of "{user_input}"
2. EXACTLY {num_songs} song recommendations with their artists
3. A short description of the playlist

Format your response as:
## [Playlist Name]

1. [Song Title] by [Artist]
- A short reason it fits
2. [Song Title] by [Artist]
A short reason it fits
...and so on until you reach {num_songs} songs.

IMPORTANT: You MUST include EXACTLY {num_songs} songs, no more and no less.
"""

    #FAL
    else:
        prompt = f"""You're a smart music assistant helping a user curate a playlist.
        
User Vibe: {user_input}

There are no similar vibes found in the system. Based on your knowledge of music:

1. Create a creative playlist name that captures the essence of "{user_input}"
2. A short description of the playlist
3. Generate EXACTLY {num_songs} song recommendations with their artists that would match this vibe perfectly

Format your response as:
## [Playlist Name]

1. [Song Title] by [Artist]
- A short reason it fits
2. [Song Title] by [Artist]
A short reason it fits
...and so on until you reach {num_songs} songs.

IMPORTANT: You MUST include EXACTLY {num_songs} songs, no more and no less. Be diverse in your recommendations while staying true to the requested vibe.
"""

    response = model.generate_content(prompt)
    return response.text

#test the agent
user_input = "I'm feeling nostalgic and want to reminisce about the past"
playlist = vibe_music_agent(user_input)
print(playlist)




    