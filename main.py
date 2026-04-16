import fitz
import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()
VOICERSS_KEY = os.getenv("VOICERSS_KEY")

# Voice RSS API endpoint
API_URL = "https://api.voicerss.org/"

# Extract text from the PDF file
pdf_path = "lighthouse.pdf"         # Replace with the actual path to your PDF file
doc = fitz.open(pdf_path)
full_text = ""
for page in doc:
    full_text += page.get_text()
doc.close()

# Clean up the extracted text
full_text = full_text.replace("\n", " ")
full_text = re.sub(r"\s+", " ", full_text)
full_text = full_text.replace("- ", "")
full_text = full_text.strip()

# Test run: Take first 500 characters to test
sample_text = full_text[:500]
print(f"Sending this text to the API:\n{sample_text}\n")

# Build the params for the request
params = {
    "key": VOICERSS_KEY,
    "src": sample_text,
    "hl": "en-us",
    "v": "Mary",
    "c": "MP3",
    "f": "44khz_16bit_stereo"
}

# Make the request to the API
response = requests.get(API_URL, params=params)

# Validate the response
if response.status_code == 200 and not response.text.startswith("Error"):
    # Save the audio bytes to a file
    with open("output.mp3", "wb") as f:
        f.write(response.content)
    print("Audio saved as output.mp3")
else:
    print(f"Error: {response.status_code}")
    print(response.text)