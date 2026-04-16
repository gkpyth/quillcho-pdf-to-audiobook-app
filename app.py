import streamlit as st
import fitz
import requests
import os
import re
from pydub import AudioSegment
from io import BytesIO
from dotenv import load_dotenv

# Load API Key
load_dotenv()
VOICERSS_KEY = os.getenv("VOICERSS_KEY")

# Page setup
st.set_page_config(page_title="Quillcho", page_icon="🪶", layout="centered")

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
    </style>
    """, unsafe_allow_html=True)

# Title with colored "cho"
st.markdown(
    "<h1>🪶 Quill<span style='color:#C4622D;'>cho</span></h1>",
    unsafe_allow_html=True
)
st.write("Turn any PDF into an audiobook. Free, simple, and right in your browser.")

# File Uploader
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

# Convert button (only shows if a file is uploaded)
if uploaded_file is not None:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        convert_clicked = st.button("Convert to Audio", type="primary", use_container_width=True)
    if convert_clicked:
        with st.spinner("Extracting text..."):
            # Read PDF from uploaded file
            pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()

            # Clean up text:
            full_text = full_text.replace("\n", " ")
            full_text = re.sub(r"\s+", " ", full_text)
            full_text = full_text.replace("- ", "")
            full_text = full_text.replace("—", ",")  # em dash → comma for proper pause
            full_text = full_text.replace("–", ",")  # en dash → comma (same reason)
            full_text = full_text.strip()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            with st.spinner("Converting to audio..."):
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

                for chunk in chunks:
                    params = {
                        "key": VOICERSS_KEY,
                        "src": chunk,
                        "hl": "en-us",
                        "v": "Mary",
                        "c": "MP3",
                        "f": "44khz_16bit_stereo"
                    }

                    response = requests.get("https://api.voicerss.org/", params=params)

                    if response.status_code == 200 and not response.text.startswith("ERROR"):
                        # Convert response bytes to AudioSegment and append
                        chunk_audio = AudioSegment.from_mp3(BytesIO(response.content))
                        combined_audio += chunk_audio
                    else:
                        st.error(f"Something went wrong: {response.text}")
                        error_occurred = True
                        break

                # Export combined audio back to bytes
                if not error_occurred:
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
