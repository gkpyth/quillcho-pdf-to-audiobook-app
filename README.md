# Quillcho

A PDF-to-audiobook web app that extracts text from PDF files and converts it to speech using the VoiceRSS API. Built with Python, Streamlit, VoiceRSS & Supabase. - part of personal bootcamp projects portfolio.

## Features
- PDF upload with drag-and-drop support
- Text extraction from PDF files via PyMuPDF
- Text-to-speech conversion via VoiceRSS API
- Page range selector for multi-page PDFs
- Voice selection (US and UK English)
- Smart text preprocessing (chapter headings, em dashes, line breaks)
- Chunked conversion with progress bar for long documents
- Automatic retry logic for API reliability
- In-browser audio playback and MP3 download
- Per-IP daily rate limiting via Supabase (hashed for privacy)
- Honeypot bot protection
- Automatic database cleanup of expired usage records
- Custom themed UI
- Privacy policy with transparent data handling disclosure

## Requirements
- Python 3
- ffmpeg (system-level dependency)
- VoiceRSS API key (free tier)
- Supabase project (free tier)

## Installation
```
pip install -r requirements.txt
```

For ffmpeg on Windows, download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add to your system PATH.

## Environment Variables
Create a `.env` file in the project root:
```
VOICERSS_KEY=your_voicerss_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_publishable_key
```

## How to Run
```
streamlit run app.py
```
The app runs at `http://localhost:8501`.

## Project Structure
```
quillcho/
├── app.py                 # Main application — UI, conversion logic, rate limiting
├── requirements.txt       # Python dependencies
├── packages.txt           # System dependencies (ffmpeg)
├── .gitignore
└── .streamlit/
    └── config.toml        # Theme configuration
```

## Supabase Setup
The app uses a single `usage_logs` table for rate limiting:

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | int8 | auto | Primary key |
| `ip_hash` | text | — | SHA-256 hashed visitor IP |
| `usage_count` | int4 | 1 | Conversions used today |
| `date` | date | now() | Date of usage |

Enable Row Level Security with permissive policies for SELECT, INSERT, UPDATE, and DELETE on the `anon` role. Old entries are automatically cleaned up on each visit.

## How It Works
1. User uploads a PDF file
2. PyMuPDF extracts text from selected pages
3. Text is preprocessed (headings, punctuation, special characters)
4. Text is split into chunks at sentence boundaries (~5000 chars)
5. Each chunk is sent to VoiceRSS API via POST request
6. Audio responses are stitched together using pydub
7. Final MP3 is available for playback and download
8. Usage is logged to Supabase after successful conversion

## Deployment
Deployed on Streamlit Cloud. Environment variables are stored as Streamlit secrets. The `packages.txt` file ensures ffmpeg is installed on the server.

For Streamlit Cloud secrets, use TOML format:
```toml
VOICERSS_KEY = "your_key"
SUPABASE_URL = "your_url"
SUPABASE_KEY = "your_key"
```

## Limitations
- Free TTS voices are limited in variety (2 decent options)
- VoiceRSS free tier allows 350 requests per day
- Users are limited to 5 conversions per day per IP
- Scanned PDFs are not supported (text-based PDFs only)
- Large PDFs take longer due to per-chunk API calls with retry delays

## Author
Ghaleb Khadra