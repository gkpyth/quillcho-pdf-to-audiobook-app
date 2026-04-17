import streamlit as st
import fitz
import requests
import os
import re
import time
import hashlib
from pydub import AudioSegment
from io import BytesIO
from dotenv import load_dotenv

# Load API Keys
try:
    # Streamlit Cloud
    VOICERSS_KEY = st.secrets["VOICERSS_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    # Local development
    load_dotenv()
    VOICERSS_KEY = os.getenv("VOICERSS_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DAILY_LIMIT = 5

# Page setup
st.set_page_config(page_title="Quillcho", page_icon="🪶", layout="centered")

def get_ip_hash():
    """Get visitor's IP and return a hashed version for privacy."""
    try:
        headers = st.context.headers
        # Try multiple headers that Streamlit Cloud might use
        ip = (
            headers.get("x-real-ip") or
            headers.get("x-forwarded-for", "unknown")
        )
        # x-forwarded-for can contain multiple IPs, take the first (original client)
        ip = ip.split(",")[0].strip()
    except Exception:
        ip = "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()

def check_usage(ip_hash):
    """Check how many conversions this IP has used today."""
    today = time.strftime("%Y-%m-%d", time.gmtime())

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/usage_logs",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params={
            "ip_hash": f"eq.{ip_hash}",
            "date": f"eq.{today}",
            "select": "usage_count",
        }
    )

    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]["usage_count"]
    return 0

def increment_usage(ip_hash):
    """Increment usage count for this IP today, or create a new entry."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    current = check_usage(ip_hash)

    if current > 0:
        # Update existing entry
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/usage_logs",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            params={
                "ip_hash": f"eq.{ip_hash}",
                "date": f"eq.{today}",
            },
            json={"usage_count": current + 1}
        )
    else:
        # Insert new entry
        requests.post(
            f"{SUPABASE_URL}/rest/v1/usage_logs",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json={
                "ip_hash": ip_hash,
                "usage_count": 1,
                "date": today,
            }
        )

def cleanup_old_entries():
    """Delete entries older than today to keep the table clean."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    requests.delete(
        f"{SUPABASE_URL}/rest/v1/usage_logs",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params={
            "date": f"lt.{today}",
        }
    )

# Custom CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700&family=DM+Sans:wght@400;500&display=swap');
    
    /* Apply fonts */
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'Syne', sans-serif !important;
    }
    
    /* Upload zone layout */
    [data-testid="stFileUploaderDropzone"] {
        min-height: 200px;
        border: 2px dashed #C4622D;
        background-color: #FFFFFF;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
    }
    
    /* The inner container holding the text and button */
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
    }
    
    /* Style the Browse files button */
    [data-testid="stFileUploaderDropzone"] button {
        background-color: #C4622D !important;
        color: white !important;
        border: none !important;
        margin-top: 1rem;
    }
    
    /* Force full width and center spinner */
    [data-testid="stSpinner"] {
        margin-left: auto !important;
        margin-right: auto !important;
    }
    
    /* Hide honeypot field */
    .st-key-url_field {
        position: absolute !important;
        left: -9999px !important;
    }
    
    </style>
    """, unsafe_allow_html=True)

# Title with colored "cho"
st.markdown(
    "<h1>🪶 Quill<span style='color:#C4622D;'>cho</span></h1>",
    unsafe_allow_html=True
)
st.write("Turn any PDF into an audiobook. Free, simple, and right in your browser.")

# Bot protection - honeypot field (invisible to users, bots auto-fill it - cool trick!)
bot_check = st.text_input("Website", key="url_field", label_visibility="hidden")

# File Uploader
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

# Convert button (only shows if a file is uploaded)
if uploaded_file is not None:
    # Read the PDF once to get the number of pages
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    doc.close()

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown(f"<p style='text-align: center;'>PDF has <strong>{total_pages}</strong> page(s)</p>", unsafe_allow_html=True)

    # Page range selector
    if total_pages > 1:
        page_range = st.slider(
            "Select pages to convert",
            min_value=1,
            max_value=total_pages,
            value=(1, total_pages),         # Default to all pages
            step=1,
        )
        start_page, end_page = page_range
    else:
        start_page, end_page = 1, 1

    # Voice selection
    voice_options = {
        "Mary (US Female)": ("Mary", "en-us"),
        "Nancy (UK Female)": ("Nancy", "en-gb"),
    }

    selected_voice = st.selectbox("Choose a voice", options=voice_options.keys())
    voice, language = voice_options[selected_voice]

    ip_hash = get_ip_hash()
    usage = check_usage(ip_hash)
    cleanup_old_entries()

    remaining = DAILY_LIMIT - usage
    if remaining <= 0:
        st.warning("You've reached today's free conversion limit. This app runs on a free text-to-speech service with daily usage caps. Please come back tomorrow.\nThank you for using Quillcho!")

    if remaining > 0:
        remaining_text = st.empty()
        remaining_text.markdown(
            f"<p style='text-align: center; color: #6B6864;'>{remaining} free conversion(s) remaining today</p>",
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            convert_clicked = st.button("Convert to Audio", type="primary", use_container_width=True)

        if convert_clicked:
            if bot_check:
                st.error("Something went wrong. Please try again.")
                st.stop()
            with st.spinner("Extracting text..."):
                # Re-open PDF from byes and extract only selected pages
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                full_text = ""
                for page_num in range(start_page - 1, end_page):
                    full_text += doc[page_num].get_text()
                doc.close()

                # Add pauses after headings and short lines without punctuation
                lines = full_text.split("\n")
                processed_lines = []
                for line in lines:
                    stripped = line.strip()
                    if stripped and len(stripped) < 60 and not stripped[-1] in ".!?,:;":
                        stripped += "."
                    processed_lines.append(stripped)
                full_text = "\n".join(processed_lines)

                # Clean up text:
                full_text = full_text.replace("\n", " ")
                full_text = re.sub(r"\s+", " ", full_text)
                full_text = full_text.replace("- ", "")
                full_text = full_text.replace("—", ",")  # em dash → comma for proper pause
                full_text = full_text.replace("–", ",")  # en dash → comma (same reason)
                full_text = full_text.strip()

            # Split text into chunks at sentence boundaries (~5000 characters)
            def chunk_text(text, max_chars=5000):
                sentences = text.split(". ")
                chunks = []
                current_chunk = ""

                for sentence in sentences:
                    # If adding this sentence would exceed the limit, save current chunk
                    if len(current_chunk) + len(sentence) > max_chars:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence + ". "
                    else:
                        current_chunk += sentence + ". "

                # Add last chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())

                return chunks

            chunks = chunk_text(full_text)
            combined_audio = AudioSegment.empty()  # start with empty audio
            error_occurred = False

            progress_bar = st.progress(0, text="Converting to audio...")

            for i, chunk in enumerate(chunks):
                params = {
                    "key": VOICERSS_KEY,
                    "src": chunk,
                    "hl": language,
                    "v": voice,
                    "c": "MP3",
                    "f": "44khz_16bit_stereo"
                }

                max_retries = 3
                success = False

                for attempt in range(max_retries):
                    try:
                        response = requests.post("https://api.voicerss.org/", data=params)

                        content_type = response.headers.get("Content-Type", "")
                        if response.status_code == 200 and "audio" in content_type:
                            chunk_audio = AudioSegment.from_mp3(BytesIO(response.content))
                            combined_audio += chunk_audio
                            success = True
                            break
                        else:
                            time.sleep(1)

                    except Exception:
                        time.sleep(1)

                if success:
                    progress = (i + 1) / len(chunks)
                    progress_bar.progress(progress, text=f"Converting part {i + 1} of {len(chunks)}...")
                    time.sleep(1)

                else:
                    st.error(f"Something went wrong with the conversion. Please try again.")
                    error_occurred = True
                    break

            # Export combined audio back to bytes
            if not error_occurred:
                progress_bar.progress(1.0, text="Conversion complete!")
                increment_usage(ip_hash)
                remaining -= 1
                remaining_text.markdown(
                    f"<p style='text-align: center; color: #6B6864;'>{remaining} free conversion(s) remaining today</p>",
                    unsafe_allow_html=True
                )
                if remaining == 0:
                    st.warning("You've used your last free conversion for today. Please come back tomorrow.\nThank you for using Quillcho!")

                output_buffer = BytesIO()
                combined_audio.export(output_buffer, format="mp3")
                audio_bytes = output_buffer.getvalue()

            if not error_occurred:
                st.success("Done!")
                st.audio(audio_bytes, format="audio/mp3")
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    st.download_button(
                        type="primary",
                        label="Download MP3",
                        data=audio_bytes,
                        file_name="audiobook.mp3",
                        mime="audio/mp3",
                        use_container_width=True
                    )
