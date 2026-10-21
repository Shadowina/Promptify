# Promptify — AI Music Vibe Discovery & Playlist Generator

Promptify translates natural language mood and vibe descriptions into curated music discoveries and Spotify playlists using semantic vector retrieval (FAISS) and Gemini AI.

---

## Architecture Overview

Promptify employs a **Retrieval-Augmented Generation (RAG)** architecture:

```
[ User Vibe Input ] ──▶ "late night heartbreak under the rain"
        │
        ▼
[ Cached FAISS Vector Store ]
        │  (Embedding model: models/text-embedding-004)
        │  Retrieves top-k closest lyric and thematic snippets
        ▼
[ Securely Bounded Prompt ]
        │  Wrapped in <retrieved_vibes> XML tags to isolate reference data
        ▼
[ Google GenAI SDK (gemini-3.5-flash) ]
        │  Schema-enforced JSON generation via Pydantic (GeneratedPlaylist)
        ▼
[ Structured Playlist Result ]
        │  Name + Short Description + Tracks with Reasonings
        ▼
[ Spotify Web API ]
        │  Matched via Search API (POST /v1/me/playlists & POST /v1/playlists/{id}/tracks)
        ▼
[ Saved to User's Spotify Account ]
```

---

## Key Features & Engineering Highlights

- **Decoupled User Flow:** Users can freely explore moods and generate recommendations without upfront authentication. Spotify OAuth is requested only when saving to Spotify.
- **In-Memory Vector Caching:** The 172-item curated corpus is embedded once and cached in memory across sessions, cutting query latency from ~15s to <1s and preventing quota exhaustion.
- **Modern Google GenAI SDK:** Powered by Google's unified `google-genai` SDK with native Pydantic schema validation (`response_schema=GeneratedPlaylist`).
- **Modern Spotify Endpoints:** Targets current non-deprecated endpoints (`POST /v1/me/playlists` and `POST /v1/playlists/{id}/tracks`) supporting both public and private playlist creation.
- **Prompt Injection Defense:** Reference snippets are encapsulated inside explicit `<retrieved_vibes>` boundary tags with strict system instructions preventing untrusted corpus text from overriding application rules.
- **Automated Test Suite:** 23 deterministic unit and integration tests covering parser resilience, safe configuration, retrieval boundaries, and Spotify integration.

---

## Quickstart & Local Setup

### 1. Prerequisites
- **Python:** 3.10+ (tested on Python 3.13.5)
- **Windows `py` launcher** or standard `python3`
- A **Google AI Studio API key** ([Get key here](https://aistudio.google.com/))
- A **Spotify Developer App** ([Create app here](https://developer.spotify.com/dashboard))

### 2. Clone and Setup Environment
```bash
git clone https://github.com/Shadowina/Promptify.git
cd Promptify

# Create and activate virtual environment
py -m venv .venv
.\.venv\Scripts\activate   # On Windows (PowerShell)
# source .venv/bin/activate  # On macOS/Linux
```

### 3. Install Dependencies
```bash
# Core application dependencies
pip install -r requirements.txt

# Development and testing dependencies
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Open `.env` and fill in your keys:
```env
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-3.5-flash

SPOTIPY_CLIENT_ID=your_spotify_client_id_here
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8501
```

> **Spotify Setup Note:**
> In your [Spotify Developer Dashboard](https://developer.spotify.com/dashboard):
> 1. Under **Redirect URIs**, add exactly `http://127.0.0.1:8501`. (Spotify requires loopback IP addresses, not `localhost`).
> 2. While in **Development Mode**, add your Spotify email under **User Management** (Spotify limits development apps to 25 whitelisted accounts).

### 5. Run the Application
```bash
streamlit run app.py
```
Open your browser at `http://127.0.0.1:8501`.

---

## Running Automated Tests

Run the full test suite with `pytest`:
```bash
pytest tests/ -v
```

All external calls to Gemini and Spotify are mocked in automated tests for deterministic, offline verification.

---

## Retrieval Quality Evaluation

Promptify includes a ground-truth retrieval evaluation dataset (`tests/data/retrieval_eval_cases.json`) and benchmark script:

```bash
python evaluate_retrieval.py
```

This measures:
- **Recall@3:** Fraction of ground-truth relevant snippets retrieved in the top 3 candidates.
- **Recall@5:** Fraction of ground-truth relevant snippets retrieved in the top 5 candidates.
- **MRR (Mean Reciprocal Rank):** How highly the first relevant candidate ranks.

---

## Project Structure

```
Promptify/
├── app.py                     # Streamlit frontend & interactive playlist curation UI
├── vibe_agent.py              # Semantic retrieval, FAISS caching, and Gemini generation
├── playlist_utils.py          # Spotify OAuth, track search, and playlist management
├── evaluate_retrieval.py      # Quantitative retrieval evaluation benchmark
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Testing dependencies (pytest, pytest-mock)
├── .env.example               # Configuration template
├── tests/
│   ├── test_config.py         # Config validation and safe import tests
│   ├── test_parser.py         # Playlist text and JSON parsing tests
│   ├── test_app_flow.py       # Input bounds and validation tests
│   ├── test_retrieval.py      # FAISS caching and prompt boundary tests
│   ├── test_spotify_utils.py  # Spotify endpoint and track extraction tests
│   ├── test_vibe_agent.py     # Gemini client and candidate fallback tests
│   └── data/
│       └── retrieval_eval_cases.json  # 12 labelled evaluation cases
└── docs/
    └── modernization/         # Architecture, audit, and decision records (ADRs)
```

---

## License
MIT License.
