# app.py -> Generates a Streamlit app with information on deepfakes. Centerpiece is an AI clone of myself (developer) that does live speech of a user-input prompt

import os
import time
import json
import base64
import requests
from requests.auth import HTTPBasicAuth

import streamlit as st
from streamlit_modal import Modal 
import streamlit.components.v1 as components


import dropbox
from elevenlabs import generate, set_api_key, Voice, VoiceSettings
from openai import OpenAI

# -----------------------------
# Optional: load .env for local dev
# -----------------------------
if os.getenv("USE_DOTENV", "false").lower() in ("1", "true", "yes"):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass  

# -----------------------------
# Environment configuration
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# D-ID credentials (either username+password flow, or API key header if you prefer)
DID_USERNAME = os.getenv("DID_USERNAME")
DID_PWD = os.getenv("DID_PWD")
DID_API_KEY = os.getenv("DID_API_KEY")

DBX_ACCESS_TOKEN = os.getenv("DBX_ACCESS_TOKEN")

# File paths (all configurable)
OUTPUT_AUDIO_PATH = os.getenv("OUTPUT_AUDIO_PATH", "output_audio.wav")
REFERENCE_IMAGE_PATH = os.getenv("REFERENCE_IMAGE_PATH", "reference_image.jpg")
FINAL_VIDEO_PATH = os.getenv("FINAL_VIDEO_PATH", "final_video.mp4")
DEFAULT_FALLBACK_VIDEO = os.getenv("DEFAULT_FALLBACK_VIDEO", "video_1.mp4")

# UI / Streamlit config
st.set_page_config(
    page_title="AI Has Distorted Your Reality",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# Basic validation & client setup
# -----------------------------
missing_required = []
if not OPENAI_API_KEY:
    missing_required.append("OPENAI_API_KEY")
# ELEVENLABS and Dropbox/D-ID are recommended at runtime; however, the app will degrade gracefully without them

if missing_required:
    st.warning("Missing required environment variables: " + ", ".join(missing_required))

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ElevenLabs key
if ELEVENLABS_API_KEY:
    set_api_key(ELEVENLABS_API_KEY)

# If using D-ID API key header instead of basic auth:
DID_HEADERS_APIKEY = {"x-api-key": DID_API_KEY} if DID_API_KEY else {}

# -----------------------------
# Helpers
# -----------------------------
def local_css(file_name: str):
    """Inject a local CSS file if it exists."""
    try:
        if os.path.exists(file_name):
            with open(file_name, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        else:
            pass
    except Exception as e:
        st.warning(f"Could not load CSS '{file_name}': {e}")

def get_video_base64(video_path: str) -> str:
    """Base64-encode a video file for HTML embedding."""
    with open(video_path, "rb") as video_file:
        return base64.b64encode(video_file.read()).decode()

def dbx_shareable_download_url(shared_obj) -> str:
    """
    Convert a Dropbox shared link to a direct-download URL.
    Dropbox often returns ?dl=0; switch to ?dl=1 (or dl.dropboxusercontent domain).
    """
    url = getattr(shared_obj, "url", "")
    if not url:
        return ""
    # Prefer ?dl=1
    if "dl=0" in url:
        url = url.replace("dl=0", "dl=1")
    elif "dl=1" not in url:
        joiner = "&" if "?" in url else "?"
        url = f"{url}{joiner}dl=1"
    # (Alternative) domain swap:
    url = url.replace("www.dropbox", "dl.dropboxusercontent")
    return url

def safe_upload_to_dropbox(dbx: dropbox.Dropbox, local_path: str) -> str:
    """
    Upload a local file to Dropbox root and return a direct-download URL.
    Returns "" on failure.
    """
    try:
        fname = os.path.basename(local_path)
        with open(local_path, "rb") as f:
            dbx.files_upload(f.read(), "/" + fname, mode=dropbox.files.WriteMode.overwrite)
        link_obj = dbx.sharing_create_shared_link("/" + fname)
        return dbx_shareable_download_url(link_obj)
    except Exception as e:
        st.error(f"Dropbox upload failed for {local_path}: {e}")
        return ""

def embed_video_tag_from_file(path: str, width: int = 550, height: int = 550, autoplay: bool = True) -> str:
    """Build an HTML5 video tag from a local file path."""
    video_base64 = get_video_base64(path)
    auto = "autoplay" if autoplay else ""
    return f"""
    <video width="{width}" height="{height}" controls {auto}>
        <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
    </video>
    """

# -----------------------------
# UI: CSS & Top Banner
# -----------------------------
# External CSS and page padding tweak
st.markdown("""
<head>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.1.1/css/all.min.css">  
</head>
<style>
    .main .block-container {{
        margin-bottom: 230px;
    }}
</style>
""", unsafe_allow_html=True)

#Loading local CSS file
local_css("style.css")

# Top banner
st.markdown("""
    <div class="backimage">
        <h1>AI Has <span style="font-family: sans-serif; font-size: 1.5em; color: black; font-weight: bolder;">Distorted</span> Your Reality</h1> 
        <h3>The technology is so good that you don't even realize when it tricks you.</h3>
        <div class="scroll">
            <h5>Scroll down to learn more</h5>
            <i class="fas fa-arrow-down" style="font-size: 1.2em;"></i>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <div style="text-align: left;">
        <h2 class="h2class">Make Me Say Anything</h2>
    </div>
""", unsafe_allow_html=True)

# -----------------------------
# UI: Input / Submit
# -----------------------------
col1, col2 = st.columns(2)
with col1:
    unformattedText = st.text_area(label="", placeholder="Enter the text you'd like my AI twin to say")

with col2:
    submit = st.button('Submit')

video_html = ""  # Placeholder to be filled below

# -----------------------------
# Main: Submit handler
# -----------------------------
if submit:
    # API guardrails
    if client is None:
        st.error("OpenAI client not configured. Set OPENAI_API_KEY in your environment.")
    else:
        with st.spinner('Creating AI twin...'):
            # 1) Reformat user input to filter inappropriate content and improve text readability
            try:
                formattedText = client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Add ellipses, quotes, punctuation, etc., to make the attached text more natural, "
                                "as I'm feeding it to Elevenlabs for a voice clone. Don't remove any punctuations/odd letters "
                                "which have already been added by a user. If the content contains inappropriate themes or harmful messages, "
                                "output: Hello, user..., would you consider changing your prompt to avoid the R-rated material!, "
                                "otherwise, output only the modified text, and nothing else."
                            ),
                        },
                        {"role": "user", "content": str(unformattedText)},
                    ],
                )
                text = formattedText.choices[0].message.content
            except Exception as e:
                st.error(f"OpenAI request failed: {e}")
                text = None

            # 2) Generating user-inputted spoken audio with ElevenLabs
            audio_ok = False
            if text and ELEVENLABS_API_KEY:
                try:
                    voiceModel = "eleven_multilingual_v2"
                    voice = Voice(
                        voice_id="7vmK1wB4cISJLtk5nOyY",
                        settings=VoiceSettings(stability=0.8, similarity_boost=0.94, style=0.05, use_speaker_boost=False),
                    )
                    audio_bytes = generate(text=text, voice=voice, model=voiceModel)
                    with open(OUTPUT_AUDIO_PATH, "wb") as f:
                        f.write(audio_bytes)
                    audio_ok = True
                except Exception as e:
                    st.error(f"ElevenLabs generation failed: {e}")
            elif text and not ELEVENLABS_API_KEY:
                st.warning("ELEVENLABS_API_KEY not set — skipping audio generation.")

            # 3) Uploading files to cloud (Dropbox)
            audiolink, imagelink = "", ""
            if audio_ok and DBX_ACCESS_TOKEN:
                if not os.path.exists(REFERENCE_IMAGE_PATH):
                    st.error(f"REFERENCE_IMAGE_PATH not found: {REFERENCE_IMAGE_PATH}. "
                             f"Place your reference image or set the env var accordingly.")
                try:
                    dbx = dropbox.Dropbox(DBX_ACCESS_TOKEN)
                    # Upload audio
                    audiolink = safe_upload_to_dropbox(dbx, OUTPUT_AUDIO_PATH)
                    # Upload image
                    if os.path.exists(REFERENCE_IMAGE_PATH):
                        imagelink = safe_upload_to_dropbox(dbx, REFERENCE_IMAGE_PATH)
                except Exception as e:
                    st.error(f"Dropbox error: {e}")
            elif audio_ok and not DBX_ACCESS_TOKEN:
                st.warning("DBX_ACCESS_TOKEN not set — skipping Dropbox upload.")

            # 4) Calling D-ID to synthesize video from image and voiceover
            did_success = False
            if audiolink and imagelink and (DID_USERNAME and DID_PWD):
                # Basic Auth flow
                try:
                    url = "https://api.d-id.com/talks"
                    headers = {"Content-Type": "application/json", "Accept": "application/json"}
                    data = {
                        "source_url": imagelink,
                        "script": {"type": "audio", "audio_url": audiolink},
                    }
                    resp = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(DID_USERNAME, DID_PWD))
                    if resp.status_code != 200:
                        st.error(f"D-ID request failed: {resp.status_code} {resp.text}")
                    else:
                        rj = resp.json()
                        talk_id = rj.get("id")
                        # Poll for result
                        result_url = None
                        for _ in range(60):  # ~120 seconds total @2s per iteration
                            time.sleep(2)
                            poll = requests.get(f"{url}/{talk_id}", headers=headers, auth=HTTPBasicAuth(DID_USERNAME, DID_PWD))
                            pj = poll.json()
                            result_url = pj.get("result_url")
                            if result_url:
                                break
                        if not result_url:
                            st.error("Timed out waiting for D-ID result.")
                        else:
                            # Download final video
                            r = requests.get(result_url, allow_redirects=True)
                            with open(FINAL_VIDEO_PATH, "wb") as vf:
                                vf.write(r.content)
                            did_success = True
                except Exception as e:
                    st.error(f"D-ID processing failed: {e}")

            elif audiolink and imagelink and DID_API_KEY and not (DID_USERNAME and DID_PWD):
                # Receiving final video as a response from D-ID
                try:
                    url = "https://api.d-id.com/talks"
                    headers = {"Content-Type": "application/json", "Accept": "application/json", **DID_HEADERS_APIKEY}
                    data = {
                        "source_url": imagelink,
                        "script": {"type": "audio", "audio_url": audiolink},
                    }
                    resp = requests.post(url, headers=headers, json=data)
                    if resp.status_code != 200:
                        st.error(f"D-ID (API key) request failed: {resp.status_code} {resp.text}")
                    else:
                        rj = resp.json()
                        talk_id = rj.get("id")
                        result_url = None
                        for _ in range(60):
                            time.sleep(2)
                            poll = requests.get(f"{url}/{talk_id}", headers=headers)
                            pj = poll.json()
                            result_url = pj.get("result_url")
                            if result_url:
                                break
                        if not result_url:
                            st.error("Timed out waiting for D-ID result (API key flow).")
                        else:
                            r = requests.get(result_url, allow_redirects=True)
                            with open(FINAL_VIDEO_PATH, "wb") as vf:
                                vf.write(r.content)
                            did_success = True
                except Exception as e:
                    st.error(f"D-ID (API key) processing failed: {e}")
            else:
                if not (DID_USERNAME and DID_PWD) and not DID_API_KEY:
                    st.info("D-ID credentials not configured; will show fallback if available.")
                elif not (audiolink and imagelink):
                    st.info("Missing Dropbox links; cannot call D-ID. Check DBX_ACCESS_TOKEN and file paths.")

            # 5) Display a final video result if available
            if did_success and os.path.exists(FINAL_VIDEO_PATH):
                video_html = embed_video_tag_from_file(FINAL_VIDEO_PATH, autoplay=True)
            else:
                if os.path.exists(DEFAULT_FALLBACK_VIDEO):
                    video_html = embed_video_tag_from_file(DEFAULT_FALLBACK_VIDEO, autoplay=True)
                else:
                    st.warning("No video available. Provide a fallback video file or configure D-ID properly.")
                    video_html = ""
else:
    # Initial page load (if no user submission) -> show fallback demo video
    if os.path.exists(DEFAULT_FALLBACK_VIDEO):
        video_html = embed_video_tag_from_file(DEFAULT_FALLBACK_VIDEO, autoplay=True)
    else:
        video_html = ""

# Render the video for web display
if video_html:
    st.markdown(video_html, unsafe_allow_html=True)

# -----------------------------
# Bottom section -> additional information on deepfakes
# -----------------------------
st.markdown("""
    <div style="text-align: left;" class="bottomsection">
        <h2 class="h2class" id="bottom">Know How This Works</h2>
        <p id="bottom">This website lets you interact with a <span class="highlight">deepfake</span>.</p>
        <p id="bottom">These are made by enhancing audio and images with AI to create scenes which never actually happened in the real world.</p>
        <p id="bottom">This project has used the best <span class="highlight">cheap</span> AI tools to create the deepfake <span class="highlight">from scratch</span>.</p>
        <a href="https://www.youtube.com/embed/qcJ4buwMPTE" style="font-weight: bold;" id="bottom">Check out a professional deepfake</a>
    </div>
""", unsafe_allow_html=True)
