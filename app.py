
import logging
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.audiclabs_client import AudicLabsClient
from src.dubbing_pipeline import DubbingPipeline

load_dotenv()
logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="AI Video Dubbing Studio | AudicLabs",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------- THEME -----------------------

st.markdown(
    """
    <style>
    :root {
        --bg: #070b18;
        --panel: #101a32;
        --panel2: #0b1429;
        --border: #253d69;
        --text: #edf3ff;
        --muted: #a8b9da;
        --cyan: #27d9ff;
        --purple: #a855f7;
        --pink: #ff3d9a;
        --orange: #ffad26;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--bg) !important;
        color: var(--text) !important;
    }

    [data-testid="stHeader"] {
        background: var(--bg) !important;
        height: 0rem !important;
        visibility: hidden;
    }

    [data-testid="stToolbar"] {
        right: 1rem;
    }

    [data-testid="stAppViewContainer"] .main {
        background: var(--bg) !important;
    }

    .block-container {
        max-width: 1500px !important;
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1830 0%, #080e20 100%);
        border-right: 1px solid #263d68;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.4rem;
    }

    h1, h2, h3, p, label, span, div {
        font-family: Inter, "Segoe UI", sans-serif;
    }

    .brand {
        font-size: 1.65rem;
        font-weight: 850;
        line-height: 1.25;
        background: linear-gradient(
            90deg, #22d3ee, #818cf8, #e879f9, #fb7185, #fbbf24
        );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.4rem;
    }

    .hero {
        position: relative;
        overflow: hidden;
        padding: 2.0rem 2rem 1.6rem;
        border: 1px solid #344b85;
        border-radius: 20px;
        background:
            radial-gradient(ellipse at 0% 0%, #192c63 0%, transparent 45%),
            radial-gradient(ellipse at 100% 0%, #43145e 0%, transparent 42%),
            linear-gradient(135deg, #101b39, #090f23 80%);
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.22);
        margin-bottom: 1.3rem;
    }

    .hero:before {
        content: "";
        position: absolute;
        height: 4px;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(
            90deg, #00d9ff, #535cff, #c026d3, #ff3294, #ffad26
        );
    }

    .hero-title {
        font-size: clamp(2rem, 3.5vw, 3.3rem);
        line-height: 1.15;
        font-weight: 900;
        letter-spacing: -1.5px;
        background: linear-gradient(
            90deg, #38e8ff, #818cf8, #e879f9, #ff4caa, #ffbd43
        );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 .65rem;
    }

    .hero-description {
        color: #c5d5f6;
        font-size: 1.05rem;
        line-height: 1.7;
        max-width: 850px;
        margin: 0;
    }

    .feature-row {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        margin-top: 1.4rem;
    }

    .feature {
        flex: 1 1 180px;
        color: #bcd3ff;
        background: rgba(25, 45, 88, .55);
        border: 1px solid #293e70;
        padding: .8rem 1rem;
        border-radius: 12px;
        font-size: .9rem;
    }

    .feature strong {
        color: #63dfff;
        display: block;
        margin-bottom: .25rem;
    }

    .section-title {
        font-size: 1.65rem;
        font-weight: 800;
        background: linear-gradient(90deg, #22d3ee, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: .2rem;
    }

    .section-subtitle {
        color: var(--muted);
        margin-bottom: 1.1rem;
    }

    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: .6rem;
        border-bottom: 1px solid #263d68;
        background: transparent;
    }

    [data-testid="stTabs"] button[data-baseweb="tab"] {
        color: #a9badb !important;
        font-weight: 700;
        padding: .8rem 1rem;
        border-radius: 10px 10px 0 0;
    }

    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #ff5ba7 !important;
        border-bottom: 3px solid #ff3d9a !important;
        background: rgba(255, 61, 154, .07);
    }

    [data-testid="stFileUploader"] {
        background: linear-gradient(135deg, #0e1a33, #101a30);
        border: 1px dashed #3987ec;
        border-radius: 14px;
        padding: .5rem;
    }

    [data-testid="stFileUploader"] section {
        background: transparent !important;
    }

    [data-testid="stFileUploader"] button {
        background: linear-gradient(100deg, #1767ee, #9333ea) !important;
        color: white !important;
        border: none !important;
        border-radius: 9px !important;
        font-weight: 700 !important;
    }

    [data-testid="stTextInput"] input {
        background: #111e38 !important;
        color: #f4f7ff !important;
        border: 1px solid #354d7b !important;
        border-radius: 9px !important;
    }

    [data-testid="stTextInput"] label,
    [data-testid="stSelectbox"] label {
        color: #d5e3ff !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        color: #fff !important;
        background: linear-gradient(
            100deg, #4f46e5, #c026d3, #f43f80, #f59e0b
        ) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 750 !important;
        min-height: 2.8rem;
        box-shadow: 0 5px 20px rgba(147, 51, 234, .15);
        transition: transform .15s ease, filter .15s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        filter: brightness(1.15);
        transform: translateY(-1px);
        color: white !important;
    }

    [data-testid="stAlert"] {
        background: #111e38;
        color: #e7efff;
        border-radius: 10px;
    }

    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #22d3ee, #a855f7, #ff3d9a);
    }

    [data-testid="stMetric"] {
        background: #101a32;
        border: 1px solid #293e70;
        border-radius: 12px;
        padding: 1rem;
    }


    /* -------- Sidebar readability fixes -------- */

    [data-testid="stSidebar"] {
        background: #0c162d !important;
        color: #f1f5ff !important;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #dce7ff !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #f8faff !important;
        font-weight: 800 !important;
    }

    [data-testid="stSidebar"] [data-testid="stTextInput"] label {
        color: #e4edff !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] input {
        background: #142442 !important;
        color: #ffffff !important;
        border: 1px solid #5573a8 !important;
        caret-color: #ffffff !important;
    }

    [data-testid="stSidebar"] input::placeholder {
        color: #a9bbdc !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebar"] [data-testid="stAlert"] {
        background: #102c36 !important;
        border: 1px solid #1c806d !important;
        color: #a7f3d0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stAlert"] p,
    [data-testid="stSidebar"] [data-testid="stAlert"] span {
        color: #a7f3d0 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #35496d !important;
    }

    [data-testid="stSidebar"] a {
        color: #75dfff !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] a:hover {
        color: #f0abfc !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #dce7ff !important;
    }

    [data-testid="stSidebar"] .brand {
        font-size: 1.55rem !important;
        line-height: 1.35 !important;
    }

    /* Improve readability of the main upload section */

    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] {
        color: #cbd8f3 !important;
    }

    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploader"] small {
        color: #e1eaff !important;
    }

    [data-testid="stFileUploader"] button {
        color: #ffffff !important;
    }


/* Dark theme for dropdowns and their selected values */
div[data-baseweb="select"] > div {
    background-color: #111c35 !important;
    border: 1px solid #35d8ff !important;
    border-radius: 8px !important;
    color: #ffffff !important;
}

/* Selected text */
div[data-baseweb="select"] input,
div[data-baseweb="select"] div,
div[data-baseweb="select"] span {
    color: #ffffff !important;
}

/* Dropdown arrow */
div[data-baseweb="select"] svg {
    fill: #35d8ff !important;
}

/* Dropdown options menu */
ul[role="listbox"] {
    background-color: #111c35 !important;
}

li[role="option"] {
    background-color: #111c35 !important;
    color: #ffffff !important;
}

li[role="option"]:hover {
    background-color: #24385c !important;
    color: #35d8ff !important;
}

/* Selected or highlighted option */
li[role="option"][aria-selected="true"] {
    background-color: #24385c !important;
    color: #35d8ff !important;
}


    hr {
        border-color: #263d68 !important;
    }

    .footer {
        border-top: 1px solid #263d68;
        padding-top: 1rem;
        margin-top: 2rem;
        color: #8da4cc;
        font-size: .85rem;
        text-align: center;
    }

    #MainMenu, footer {
        visibility: hidden;
    }


/* Dark sidebar expander headers */
section[data-testid="stSidebar"] [data-testid="stExpander"] details,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    background: #0d1830 !important;
    color: #e8f2ff !important;
    border: 1px solid #24385c !important;
    border-radius: 8px !important;
}

/* Keep expander header text and icons readable */
section[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary span,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
    color: #35d8ff !important;
    fill: #35d8ff !important;
}

/* Dark background inside expanded configuration */
section[data-testid="stSidebar"] [data-testid="stExpander"] details > div {
    background: #0d1830 !important;
    border-color: #24385c !important;
}

    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------- SIDEBAR -----------------------

with st.sidebar:
    st.markdown('<div class="brand">🎙️ AI Video<br> Dubbing Studio</div>',
                unsafe_allow_html=True)


    with st.expander("⚙️ Configuration", expanded=True):
        language_options = {
            "Hindi": "hi-IN",
            "English (US)": "en-US",
            "English (India)": "en-IN",
            "Telugu": "te-IN",
            "Tamil": "ta-IN",
            "Kannada": "kn-IN",
            "Malayalam": "ml-IN",
            "Bengali": "bn-IN",
            "Marathi": "mr-IN",
            "Gujarati": "gu-IN",
            "Punjabi": "pa-IN",
            "Spanish": "es-ES",
            "French": "fr-FR",
            "German": "de-DE",
            "Japanese": "ja-JP",
        }

        selected_language = st.selectbox(
            "Target language",
            options=list(language_options.keys()),
            index=0,
            key="target_language_dropdown",
        )
        target_language = language_options[selected_language]

        source_language = st.text_input(
            "Source language code (optional)",
            value="",
            placeholder="e.g. en-US (leave blank for auto)",
            help="Leave blank to use automatic source-language detection.",
        )

    st.divider()

    with st.expander("🔐 API credentials", expanded=False):
        if os.getenv("AUDICLABS_API_KEY"):
            st.success("API key loaded from .env")
        else:
            st.error("API key missing from .env")

        st.caption("Never share or commit your API key.")

    st.markdown("### 🧭 Quick links")
    st.markdown("- 🎬 Single video")
    st.markdown("- 📁 Batch processing")
    st.markdown("- 🧪 API diagnostics")

    st.divider()
    st.markdown(
        "**Developed by**\n\n"
        "### <span style='color:#35d8ff'>Khaja Mainuddin</span>",
        unsafe_allow_html=True,
    )

# ----------------------- HERO -----------------------

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">AI Video Dubbing Studio</div>
        <p class="hero-description">
            Translate speech, preserve speaker turns, generate dubbed audio,
            and export synchronized subtitles.
        </p>
        <div class="feature-row">
            <div class="feature">
                <strong>🎧 Speech translation</strong>
                Multilingual dubbing workflow
            </div>
            <div class="feature">
                <strong>👥 Speaker preservation</strong>
                Speaker-specific voice assignment
            </div>
            <div class="feature">
                <strong>🎙️ AI voice synthesis</strong>
                Generated speech fitted to timeline
            </div>
            <div class="feature">
                <strong>📄 Subtitle export</strong>
                Download translated SRT files
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------- HELPERS -----------------------

def save_uploaded_file(uploaded_file):
    input_dir = Path("samples/input")
    input_dir.mkdir(parents=True, exist_ok=True)

    # Avoid collisions between files with the same name.
    safe_name = Path(uploaded_file.name).name
    destination = input_dir / safe_name
    destination.write_bytes(uploaded_file.getvalue())
    return destination


def run_video(uploaded_file, language, source):
    input_path = save_uploaded_file(uploaded_file)
    progress_bar = st.progress(0)
    status = st.empty()

    def update_progress(stage, fraction):
        status.info(f"**{stage}**")
        progress_bar.progress(max(0, min(100, int(fraction * 100))))

    pipeline = DubbingPipeline()
    result = pipeline.run(
        input_path,
        target_language=language,
        source_language=source or None,
        progress=update_progress,
    )

    status.success("Processing completed.")
    return result


def show_outputs(result, original_bytes=None):
    st.markdown("### ✨ Results")

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("#### 🎬 Original video")
        if original_bytes:
            st.video(original_bytes)

    with right:
        st.markdown("#### 🎙️ Dubbed video")
        st.video(result["video"])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            "⬇️ Download dubbed video",
            data=Path(result["video"]).read_bytes(),
            file_name=Path(result["video"]).name,
            mime="video/mp4",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "⬇️ Download translated SRT",
            data=Path(result["subtitles"]).read_bytes(),
            file_name=Path(result["subtitles"]).name,
            mime="application/x-subrip",
            use_container_width=True,
        )

    with col3:
        st.download_button(
            "⬇️ Download timing report",
            data=Path(result["report"]).read_bytes(),
            file_name=Path(result["report"]).name,
            mime="application/json",
            use_container_width=True,
        )

    if result.get("segments"):
        st.markdown("#### 📝 Translated segments")
        rows = [
            {
                "Start (s)": round(float(item["start"]), 2),
                "End (s)": round(float(item["end"]), 2),
                "Speaker": item.get("speaker", "unknown"),
                "Original text": item.get("original_text", ""),
                "Translation": item.get("translated_text", ""),
                "TTS speed": item.get("speed", 1.0),
            }
            for item in result["segments"]
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


# ----------------------- TABS -----------------------

single_tab, batch_tab, diagnostics_tab = st.tabs(
    ["🎬  Single video", "📁  Batch processing", "🧪  API diagnostics"]
)

with single_tab:
    st.markdown('<div class="section-title">Dub a video</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        'Upload a short video, select the target language, and generate a dubbed version.'
        '</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Choose a video file",
        type=["mp4", "mov", "mkv"],
        help="Recommended: a short 1–5 minute video. Keep within the API size limits.",
        key="single_video",
    )

    if uploaded:
        st.video(uploaded.getvalue())
        st.caption(f"Selected file: {uploaded.name} · {uploaded.size / (1024 * 1024):.1f} MB")

    if st.button(
        "🚀 Generate dubbed video",
        type="primary",
        use_container_width=True,
        key="generate_single",
    ):
        if not uploaded:
            st.warning("Please upload a video first.")
        elif not os.getenv("AUDICLABS_API_KEY"):
            st.error("AUDICLABS_API_KEY is missing. Check your local .env file.")
        elif not target_language.strip():
            st.warning("Enter a target language code.")
        else:
            try:
                with st.spinner("Preparing dubbing pipeline..."):
                    result = run_video(
                        uploaded,
                        target_language.strip(),
                        source_language.strip(),
                    )
                show_outputs(result, uploaded.getvalue())
            except Exception as exc:
                logging.exception("Single-video processing failed")
                st.error(f"Processing failed: {exc}")
                st.info(
                    "Check API permissions, available credits, translation "
                    "provider configuration, and API response formats."
                )

with batch_tab:
    st.markdown('<div class="section-title">Batch processing</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        'Select multiple videos and process them sequentially.'
        '</div>',
        unsafe_allow_html=True,
    )

    batch_files = st.file_uploader(
        "Choose multiple videos",
        type=["mp4", "mov", "mkv"],
        accept_multiple_files=True,
        key="batch_videos",
    )

    if batch_files:
        st.info(f"{len(batch_files)} video(s) selected.")

    if st.button(
        "🚀 Process batch",
        type="primary",
        use_container_width=True,
        key="process_batch",
    ):
        if not batch_files:
            st.warning("Select at least one video.")
        elif not os.getenv("AUDICLABS_API_KEY"):
            st.error("API key missing. Check your .env file.")
        else:
            for index, batch_file in enumerate(batch_files, start=1):
                st.markdown(f"#### Video {index}/{len(batch_files)}: {batch_file.name}")
                try:
                    result = run_video(
                        batch_file,
                        target_language.strip(),
                        source_language.strip(),
                    )
                    st.success(f"Completed: {batch_file.name}")
                    show_outputs(result)
                except Exception as exc:
                    logging.exception("Batch item failed")
                    st.error(f"Failed: {batch_file.name} — {exc}")

with diagnostics_tab:
    st.markdown('<div class="section-title">API diagnostics</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        'Check free language and voice lookups before processing a video.'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "🧪 Test API lookups",
        type="primary",
        use_container_width=True,
        key="test_api",
    ):
        try:
            client = AudicLabsClient()
            with st.spinner("Loading supported languages and voices..."):
                stt_languages = client.get_stt_languages()
                tts_languages = client.get_tts_languages()
                voices = client.get_tts_voices()

            st.success("Lookup requests succeeded.")
            c1, c2, c3 = st.columns(3)
            c1.metric("STT language data", "Loaded")
            c2.metric("TTS language data", "Loaded")
            c3.metric("Voice data", "Loaded")

            with st.expander("Speech-to-text languages"):
                st.json(stt_languages)

            with st.expander("Text-to-speech languages"):
                st.json(tts_languages)

            with st.expander("Available voices"):
                st.json(voices)

        except Exception as exc:
            logging.exception("API diagnostics failed")
            st.error(f"API lookup failed: {exc}")

# ----------------------- FOOTER -----------------------

st.markdown(
    """
    <div class="footer">
        AI Video Dubbing Studio · AudicLabs AL-AI-06 Assessment<br>
        Developed by <strong style="color:#55dfff">Khaja Mainuddin</strong>
        · Review timing reports and output quality before submission.
    </div>
    """,
    unsafe_allow_html=True,
)
