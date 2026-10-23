import sys
import json
import subprocess
from pathlib import Path

from pydub import AudioSegment


def run_ffmpeg(command):
    """Run FFmpeg and raise a useful error if it fails."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed:\n{result.stderr[-2000:]}"
        )
    return result


def get_duration(path):
    """Return media duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def extract_audio(video_path, output_path):
    """Extract mono 16 kHz WAV for speech processing."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", str(output_path),
    ])
    return output_path


def extract_original_audio(video_path, output_path):
    """Extract original audio as PCM WAV."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-c:a", "pcm_s16le", str(output_path),
    ])
    return output_path


def save_bytes(data, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(data)
    return output_path


def create_dub_timeline(segments, output_path, total_duration_ms):
    """Place generated speech at the original timeline positions."""
    timeline = AudioSegment.silent(
        duration=max(1, int(total_duration_ms)),
        frame_rate=24000,
    )

    for segment in segments:
        audio_path = segment.get("audio_path")
        if not audio_path or not Path(audio_path).exists():
            continue

        clip = AudioSegment.from_file(audio_path)
        start_ms = max(0, int(float(segment["start"]) * 1000))
        end_ms = max(start_ms, int(float(segment["end"]) * 1000))
        slot_ms = end_ms - start_ms

        if slot_ms <= 0:
            continue

        # Keep this as a fallback only; the pipeline should fit TTS first.
        if len(clip) > slot_ms:
            clip = clip[:slot_ms]

        if start_ms < len(timeline):
            timeline = timeline.overlay(clip, position=start_ms)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    timeline.export(output_path, format="wav")
    return output_path


def separate_vocals_and_background(
    original_audio_path,
    output_dir,
    model="htdemucs",
    device="cpu",
):
    """
    Separate vocals from accompaniment using Demucs.

    Returns a dictionary with:
        vocals_path: estimated original speech/vocals
        background_path: estimated accompaniment

    Separation is an estimate: speech, music, and effects may leak
    between stems. Requires the Demucs model to be available locally
    or downloadable on its first run.
    """
    original_audio_path = Path(original_audio_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    separation_root = output_dir / "demucs"
    separation_root.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable, "-m", "demucs",
        "--two-stems", "vocals",
        "-n", model,
        "-d", device,
        "-o", str(separation_root),
        str(original_audio_path),
    ]

    run_ffmpeg(command)  # Raises a useful error if Demucs fails.

    stem_dir = separation_root / model / original_audio_path.stem
    vocals_path = stem_dir / "vocals.wav"
    background_path = stem_dir / "no_vocals.wav"

    if not vocals_path.exists() or not background_path.exists():
        raise FileNotFoundError(
            "Demucs completed but expected stems were not found. "
            f"Checked: {stem_dir}"
        )

    return {
        "vocals_path": str(vocals_path),
        "background_path": str(background_path),
    }


def mix_background_and_dub(
    original_audio_path,
    dubbed_audio_path,
    output_path,
    background_gain_db=-6,
    background_audio_path=None,
):
    """
    Mix the dub with a background-only stem when supplied.

    If background_audio_path is omitted, the original full mix is used
    as a fallback. In that fallback, original speech can remain audible.
    """
    background_source = background_audio_path or original_audio_path
    background = AudioSegment.from_file(background_source)
    dubbed = AudioSegment.from_file(dubbed_audio_path)

    background = background + background_gain_db

    # Use the longer track so the full video audio timeline is retained.
    duration = max(len(background), len(dubbed))
    background = background[:duration]
    dubbed = dubbed[:duration]

    mixed = background.overlay(dubbed)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    mixed.export(output_path, format="wav")
    return output_path


def mux_audio_video(video_path, audio_path, output_path):
    """Replace video audio with the assembled dub mix."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ])
    return output_path


def write_json(data, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path
