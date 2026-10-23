# AI Video Dubbing — AudicLabs Assessment

**AL-AI-06 | AI Video Dubbing: Translate and Re-Voice Short Videos**

An AI-powered video dubbing application that translates spoken dialogue into a target language, generates dubbed speech, synchronizes the new audio with the original video, and produces translated subtitles.

<<<<<<< HEAD
**Developer:** Khaja Mainuddin
=======
**Developer:** Khaja Mainuddin  
>>>>>>> origin/main
**Repository:** https://github.com/Mainuddin123/Audiclabs-video-dubbing

---

## Overview

The application provides a Streamlit interface for processing individual videos or multiple videos in a batch. It uses AudicLabs audio services, a configurable translation adapter, text-to-speech synthesis, audio processing, and FFmpeg-based media assembly to create dubbed videos.

The pipeline is designed to preserve the original video's background music and sound effects while replacing the original dialogue with synthesized speech in the selected target language.

## Key Features

- **Video upload:** Upload and process individual videos.
- **Batch processing:** Submit multiple videos for processing through the application.
- **Audio processing:** Extract audio, apply denoising, and perform speaker diarization.
- **Speech transcription:** Obtain timestamped speech segments.
- **Modular translation:** Use a configurable translation provider and fallback models.
- **Speech synthesis:** Generate target-language speech using available voices.
- **Timeline synchronization:** Fit generated speech to original segment durations where possible.
- **Background audio preservation:** Use source separation to retain background music and sound effects.
- **Subtitle generation:** Export translated dialogue as an SRT file.
- **Progress and preview:** View processing progress and compare the original and dubbed videos.
- **Evaluation:** Calculate segment timing metrics and summarize human feedback.
- **API diagnostics:** Check available language and voice information and diagnose service errors.

## Architecture

```text
Video Upload
     |
     v
Audio Extraction (FFmpeg)
     |
     v
Denoising and Speaker Diarization
     |
     v
Timestamped Speech Transcription
     |
     v
Translation Adapter
     |
     v
Text-to-Speech Synthesis
     |
     v
Segment Timing and Audio Alignment
     |
     +-----------------------------+
     |                             |
     v                             v
Dubbed Speech                 Background Audio
     |                       (Source Separation)
     +-------------+---------------+
                   |
                   v
          Audio Timeline Assembly
                   |
                   v
       Video Muxing and SRT Export
                   |
                   v
       Dubbed Video and Evaluation
```

## Technology Stack

| Component | Technology |
|---|---|
| User interface | Streamlit |
| Programming language | Python |
| Audio/video processing | FFmpeg, FFprobe, FFmpeg-Python, Pydub |
| Audio analysis | Librosa, SoundFile, NumPy |
| Source separation | Demucs |
| Audio services | AudicLabs API |
| Translation | Configurable translation API adapter |
| Data handling | Pandas |
| Evaluation | Custom timing metrics and human feedback summaries |
| Testing | Pytest |
| Configuration | Environment variables and python-dotenv |

## Project Structure

```text
audiclabs-video-dubbing/
├── app.py
├── src/
│   ├── audiclabs_client.py
│   ├── audio_processing.py
│   ├── dubbing_pipeline.py
│   ├── evaluation.py
│   ├── subtitles.py
│   └── translation.py
├── tests/
├── samples/
│   ├── input/
│   └── output/
├── outputs/                 # Local generated files; not committed
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-lock.txt
└── README.md
```

## Prerequisites

- Python 3.11 or a compatible Python version supported by the pinned dependencies
- FFmpeg and FFprobe installed and available on your system `PATH`
- AudicLabs API credentials
- Credentials for the configured translation provider
- Internet access for API-based processing

Verify the media tools:

```bash
ffmpeg -version
ffprobe -version
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Mainuddin123/Audiclabs-video-dubbing.git
cd Audiclabs-video-dubbing
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For a fully pinned environment, install from `requirements-lock.txt` if the lock file is compatible with your operating system and Python version.

### 4. Configure environment variables

Copy `.env.example` to `.env` and add your own credentials locally.

```dotenv
AUDICLABS_API_KEY=
AUDICLABS_BASE_URL=https://api.audiclabs.com/v1

TRANSLATION_API_BASE_URL=
TRANSLATION_API_KEY=
TRANSLATION_MODEL=
TRANSLATION_FALLBACK_MODEL_1=
TRANSLATION_FALLBACK_MODEL_2=
```

Use the actual endpoint, model names, and credentials provided by your chosen services. Never commit `.env` or expose API keys in source code, screenshots, logs, or Git history.

### 5. Launch the application

```bash
streamlit run app.py
```

Open the local URL displayed in the terminal, usually `http://localhost:8501`.

## How to Use

1. Open the Streamlit application.
2. Select **Single Video** or **Batch Processing**.
3. Upload the video file or files.
4. Select the desired target language and configure the available options.
5. Start processing and monitor the displayed progress.
6. Preview the original and dubbed videos.
7. Download the generated dubbed video and translated subtitles.
8. Review available segment information, evaluation metrics, and API diagnostics.

The availability of specific languages and voices depends on the connected services.

## Outputs

A successful processing run may produce:

- A dubbed MP4 video
- A translated SRT subtitle file
- A JSON processing report containing segment and timing information

Generated processing files are stored locally. The exact output contents depend on the pipeline and the services used.

## Evaluation

The project evaluates segment timing by comparing original segment durations with generated speech durations. It also records speed adjustments and supports summarizing human ratings.

For the recorded sample report, the observed metrics were:

| Metric | Observed result |
|---|---:|
| Total segments | 38 |
| Segments with timing metrics | 38 |
| Speed adjustments | 23 |
| Speed adjustment percentage | 60.53% |
| Mean absolute duration difference | 0.103 seconds |
| Maximum absolute duration difference | 1.185 seconds |

These values describe one recorded processing run and are not a general performance guarantee. Duration differences alone do not establish translation quality or perceptual synchronization.

Human feedback was recorded for three dubbed videos. The feedback indicated **good** Hindi clarity, translation, and background-audio quality, with synchronization rated **acceptable**. Speech completeness was marked **yes** for all three. These are subjective listening assessments, not independent benchmark results.

## Testing

Run the automated test suite from the repository root:

```bash
python -m pytest -v
```

The current test suite covers the translation adapter, AudicLabs client error handling, subtitle generation, and evaluation utilities. Mocked tests do not guarantee that external APIs are available or that every end-to-end video-processing scenario will succeed.

## Error Handling and Reliability

The API client includes handling for common service responses, including:

- `401` / `403`: Authentication or permission problems
- `402`: Payment or quota requirements
- `413`: Request payload too large
- `422`: Invalid request data
- `429`: Rate limiting
- `503`: Temporary service unavailability

Retry behavior and delays depend on the response and client implementation. External service outages, invalid credentials, unsupported languages, and media-processing failures can still interrupt a run.

## Security

- Keep API credentials in local environment variables.
- Keep `.env` and virtual environments out of version control.
- Do not log authorization headers or secret values.
- Use `.env.example` only for blank configuration placeholders.
- Avoid committing private videos or unnecessary intermediate media.

## Assumptions and Limitations

- Translation quality depends on the selected model and language pair.
- Speaker diarization and voice assignment depend on source audio and API capabilities.
- Speech timing may require speed adjustment, and naturalness can be affected by aggressive adjustments.
- Background music preservation depends on the quality of source separation.
- Processing time and successful completion depend on video length, local resources, and external API availability.
- Evaluation metrics are descriptive and do not replace a formal human or objective speech-quality benchmark.
- End-to-end results should be validated using the intended deployment environment and representative input videos.

## Assessment Deliverables

The project submission is intended to include:

- Source code and setup documentation
- Pinned dependencies and example configuration
- Sample input and output artifacts
- Automated tests
- A short demonstration recording
- A 1–2 page project write-up containing methodology, results, limitations, and reproducible metrics

## Author


**Khaja Mainuddin**
GitHub: https://github.com/Mainuddin123

---

*Developed as part of the AudicLabs India AL-AI-06 AI Video Dubbing assessment.*
