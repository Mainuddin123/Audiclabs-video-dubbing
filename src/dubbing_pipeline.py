
import hashlib
import json
import logging
from pathlib import Path

from pydub import AudioSegment

from src.audiclabs_client import AudicLabsClient
from src.audio_processing import (
    extract_audio,
    extract_original_audio,
    save_bytes,
    create_dub_timeline,
    mix_background_and_dub,
    mux_audio_video,
    get_duration,
    write_json,
    separate_vocals_and_background,
)
from src.subtitles import write_srt
from src.translation import TranslationAdapter

logger = logging.getLogger(__name__)


class DubbingPipeline:
    """Translate and dub video speech using AudicLabs, Gemini, and Demucs."""

    def __init__(self, output_dir="outputs", translator=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = AudicLabsClient()
        self.translator = translator or TranslationAdapter()

    @staticmethod
    def _cache_key(*values):
        raw = json.dumps(values, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cached_json(self, name, key, operation):
        cache_dir = self.output_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"{name}_{key}.json"

        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Invalid cache entry: %s", path)

        result = operation()
        path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return result

    @staticmethod
    def _segments(response):
        """Normalize common diarization response structures."""
        if isinstance(response, list):
            items = response
        elif isinstance(response, dict):
            items = (
                response.get("segments")
                or response.get("results")
                or response.get("utterances")
                or []
            )
        else:
            items = []

        normalized = []

        for item in items:
            if not isinstance(item, dict):
                continue

            start = item.get("start", item.get("start_time"))
            end = item.get("end", item.get("end_time"))

            try:
                start = float(start)
                end = float(end)
            except (TypeError, ValueError):
                continue

            if start < 0 or end <= start:
                continue

            normalized.append({
                "start": start,
                "end": end,
                "speaker": str(
                    item.get("speaker")
                    or item.get("speaker_id")
                    or "speaker_1"
                ),
                "original_text": str(item.get("text") or "").strip(),
            })

        return sorted(normalized, key=lambda item: item["start"])

    def _voice_map(self, target_language, speakers, overrides=None):
        """
        Select available voices.

        Hindi uses voice_priya_en_in because its Hindi output was tested
        successfully with language='hi'. Other languages need an explicit
        speaker override until a compatible voice has been tested.
        """
        response = self.client.get_tts_voices()

        if isinstance(response, list):
            voices = response
        elif isinstance(response, dict):
            voices = response.get("voices") or response.get("data") or []
        else:
            voices = []

        if not voices:
            raise RuntimeError("No TTS voices returned by AudicLabs.")

        def get_voice_id(voice):
            if not isinstance(voice, dict):
                return None
            return (
                voice.get("id")
                or voice.get("voice_id")
                or voice.get("name")
            )

        available = {
            get_voice_id(voice)
            for voice in voices
            if get_voice_id(voice)
        }

        target = target_language.strip().lower().replace("_", "-")
        base = target.split("-")[0]

        # Normalize language names as well as language codes.
        language_aliases = {
            "hindi": "hi",
            "telugu": "te",
            "english": "en",
            "tamil": "ta",
            "kannada": "kn",
            "malayalam": "ml",
        }
        base = language_aliases.get(base, base)

        # Hindi voice confirmed by the user's direct audio test.
        tested_voice_mappings = {
            "hi": "voice_priya_en_in",
        }

        overrides = overrides or {}
        assignments = {}

        for speaker in sorted(set(speakers)):
            selected = overrides.get(speaker)

            if selected:
                if selected not in available:
                    raise ValueError(
                        f"Voice override '{selected}' for {speaker} "
                        "was not found in the available voice list."
                    )
            else:
                selected = tested_voice_mappings.get(base)

                if not selected:
                    raise RuntimeError(
                        f"No tested voice mapping exists for "
                        f"'{target_language}'. Supply a voice override "
                        "for each speaker and test that voice with "
                        "the target language first."
                    )

                if selected not in available:
                    raise RuntimeError(
                        f"Configured voice '{selected}' is not available."
                    )

            assignments[speaker] = selected

        return assignments

    def _get_separated_stems(self, original_audio, work_dir):
        """Reuse valid Demucs stems or run source separation."""
        stem_dir = (
            work_dir
            / "demucs"
            / "htdemucs"
            / Path(original_audio).stem
        )
        vocals = stem_dir / "vocals.wav"
        background = stem_dir / "no_vocals.wav"

        if vocals.is_file() and background.is_file():
            return {
                "vocals_path": str(vocals),
                "background_path": str(background),
            }

        return separate_vocals_and_background(
            original_audio,
            work_dir,
            model="htdemucs",
            device="cpu",
        )

    def run(
        self,
        video_path,
        target_language,
        source_language=None,
        voice_overrides=None,
        progress=None,
    ):
        video_path = Path(video_path).resolve()

        if not video_path.is_file():
            raise FileNotFoundError(f"Video not found: {video_path}")

        run_id = hashlib.sha256(
            f"{video_path}:{video_path.stat().st_size}:"
            f"{video_path.stat().st_mtime_ns}:{target_language}".encode()
        ).hexdigest()[:12]

        work_dir = self.output_dir / run_id
        work_dir.mkdir(parents=True, exist_ok=True)

        def update(stage, fraction):
            if progress:
                progress(stage, fraction)

        # 1. Extract original audio.
        update("Extracting audio", 0.04)
        original_audio = work_dir / "original_audio.wav"

        if not original_audio.exists():
            extract_original_audio(video_path, original_audio)

        duration = get_duration(video_path)

        # 2. Separate speech/vocals from background music and effects.
        update("Separating vocals and background", 0.10)
        stems = self._get_separated_stems(original_audio, work_dir)

        vocal_audio = Path(stems["vocals_path"])
        background_audio = Path(stems["background_path"])

        if not vocal_audio.is_file() or not background_audio.is_file():
            raise RuntimeError("Demucs did not produce both audio stems.")

        speech_audio = work_dir / "speech_input.wav"
        if not speech_audio.exists():
            extract_audio(vocal_audio, speech_audio)

        # 3. Denoise speech; cache API output to avoid repeat charges.
        update("Noise suppression", 0.18)
        audio_hash = hashlib.sha256(speech_audio.read_bytes()).hexdigest()

        def denoise_operation():
            data, stats = self.client.denoise(speech_audio)
            cleaned_path = work_dir / "cleaned.wav"
            save_bytes(data, cleaned_path)
            return {"path": str(cleaned_path), "stats": stats}

        denoise_info = self._cached_json(
            "denoise",
            self._cache_key(audio_hash, "audic-1"),
            denoise_operation,
        )

        cleaned_audio = Path(denoise_info["path"])
        if not cleaned_audio.is_file():
            raise FileNotFoundError(
                f"Denoised audio file is missing: {cleaned_audio}"
            )

        # 4. Speaker diarization.
        update("Speaker diarization", 0.27)
        diarization_key = self._cache_key(
            hashlib.sha256(cleaned_audio.read_bytes()).hexdigest()
        )
        diarization = self._cached_json(
            "diarization",
            diarization_key,
            lambda: self.client.diarize(cleaned_audio),
        )

        segments = self._segments(diarization)
        segments = [
            {
                **segment,
                "start": max(0.0, min(segment["start"], duration)),
                "end": max(0.0, min(segment["end"], duration)),
            }
            for segment in segments
        ]
        segments = [
            segment for segment in segments
            if segment["end"] > segment["start"]
        ]

        if not segments:
            raise RuntimeError(
                "No valid timestamped speaker segments were returned."
            )

        # 5. Transcribe each segment, reusing cached transcripts.
        update("Transcribing speech", 0.35)
        cleaned = AudioSegment.from_file(cleaned_audio)
        transcript_cache = work_dir / "transcripts.json"

        try:
            transcript_data = (
                json.loads(transcript_cache.read_text(encoding="utf-8"))
                if transcript_cache.exists()
                else []
            )
        except (json.JSONDecodeError, OSError):
            transcript_data = []

        if (
            len(transcript_data) == len(segments)
            and all(isinstance(item, dict) for item in transcript_data)
        ):
            for segment, saved in zip(segments, transcript_data):
                segment["original_text"] = saved.get("original_text", "")
        else:
            transcript_data = []

            for index, segment in enumerate(segments):
                text = segment["original_text"]

                if not text:
                    clip = cleaned[
                        int(segment["start"] * 1000):
                        int(segment["end"] * 1000)
                    ]

                    if len(clip) >= 150:
                        temp_path = work_dir / f"stt_{index:04d}.wav"
                        clip.export(temp_path, format="wav")

                        key = self._cache_key(
                            hashlib.sha256(
                                temp_path.read_bytes()
                            ).hexdigest(),
                            source_language,
                        )

                        response = self._cached_json(
                            "stt",
                            key,
                            lambda p=temp_path: self.client.transcribe(
                                p, language=source_language
                            ),
                        )

                        if isinstance(response, dict):
                            text = str(
                                response.get("text")
                                or response.get("transcript")
                                or ""
                            ).strip()
                        else:
                            logger.warning(
                                "Unexpected STT response for segment %s.",
                                index,
                            )
                    else:
                        logger.warning(
                            "Skipping STT for segment %s: "
                            "audio is shorter than 150 ms.",
                            index,
                        )

                segment["original_text"] = text
                transcript_data.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "speaker": segment["speaker"],
                    "original_text": text,
                })

            transcript_cache.write_text(
                json.dumps(
                    transcript_data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        # 6. Select target voices.
        update("Loading target voices", 0.46)
        voices = self._voice_map(
            target_language,
            [segment["speaker"] for segment in segments],
            voice_overrides,
        )

        # 7. Translate, synthesize, and fit speech to segment slots.
        update("Translating and generating speech", 0.52)
        results = []
        timing = []
        speed_adjustments = 0

        for index, segment in enumerate(segments):
            original_text = segment["original_text"]
            start, end = segment["start"], segment["end"]
            slot_seconds = end - start
            target_ms = max(1, int(slot_seconds * 1000))

            translated = ""
            audio_path = None
            speed_used = 1.0
            fitted_ms = 0

            if original_text:
                translated = self.translator.translate(
                    original_text,
                    source_language or "auto-detected language",
                    target_language,
                    max_chars=max(12, int(slot_seconds * 14)),
                )

                if translated and translated.strip():
                    generated_path = work_dir / f"tts_{index:04d}.mp3"
                    voice = voices[segment["speaker"]]

                    self.client.synthesize(
                        translated,
                        voice,
                        target_language,
                        1.0,
                        generated_path,
                    )

                    generated = AudioSegment.from_file(generated_path)

                    if len(generated) > target_ms * 1.08:
                        requested_speed = min(
                            1.5, len(generated) / target_ms
                        )
                        if requested_speed > 1.0:
                            self.client.synthesize(
                                translated,
                                voice,
                                target_language,
                                requested_speed,
                                generated_path,
                            )
                            generated = AudioSegment.from_file(generated_path)
                            speed_used = requested_speed
                            speed_adjustments += 1

                    if len(generated) > target_ms:
                        generated = generated.speedup(
                            playback_speed=min(
                                len(generated) / target_ms, 1.5
                            )
                        )

                    if len(generated) > target_ms:
                        generated = generated[:target_ms]

                    fitted_path = work_dir / f"fitted_{index:04d}.wav"
                    generated.export(fitted_path, format="wav")
                    audio_path = str(fitted_path)
                    fitted_ms = len(generated)
                else:
                    logger.warning(
                        "Empty translation for segment %s; leaving it silent.",
                        index,
                    )

            results.append({
                **segment,
                "translated_text": translated,
                "voice": voices[segment["speaker"]],
                "speed": speed_used,
                "audio_path": audio_path,
            })

            timing.append({
                "segment": index,
                "speaker": segment["speaker"],
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "slot_seconds": round(slot_seconds, 3),
                "generated_seconds": round(fitted_ms / 1000, 3),
                "duration_difference_seconds": (
                    round(fitted_ms / 1000 - slot_seconds, 3)
                    if audio_path else None
                ),
                "speed": speed_used,
            })

            update(
                f"Generating segment {index + 1}/{len(segments)}",
                0.52 + 0.31 * (index + 1) / len(segments),
            )

        # 8. Assemble dubbed speech on the original timeline.
        update("Assembling dubbed audio", 0.85)
        dubbed_speech = work_dir / "dubbed_speech.wav"
        create_dub_timeline(
            results,
            dubbed_speech,
            int(duration * 1000),
        )

        # 9. Mix the dub with separated background, not the original mix.
        update("Mixing separated background audio", 0.90)
        mixed_audio = work_dir / "dubbed_mix.wav"

        mix_background_and_dub(
            original_audio,
            dubbed_speech,
            mixed_audio,
            background_gain_db=-6,
            background_audio_path=background_audio,
        )

        # 10. Export video, translated subtitles, and timing report.
        update("Exporting video and subtitles", 0.95)
        output_video = self.output_dir / f"{run_id}_dubbed.mp4"
        output_srt = self.output_dir / f"{run_id}_translated.srt"
        report_path = self.output_dir / f"{run_id}_report.json"

        mux_audio_video(video_path, mixed_audio, output_video)
        write_srt(results, output_srt)

        report = {
            "input": str(video_path),
            "target_language": target_language,
            "source_language": source_language,
            "duration_seconds": round(duration, 3),
            "segment_count": len(results),
            "voice_assignments": voices,
            "speed_adjustments": speed_adjustments,
            "timing": timing,
            "background_separation": {
                "performed": True,
                "model": "htdemucs",
                "device": "cpu",
                "vocal_stem": str(vocal_audio),
                "background_stem": str(background_audio),
                "note": (
                    "Separation is approximate; original speech or effects "
                    "may leak between stems."
                ),
            },
            "denoise_stats": denoise_info.get("stats"),
        }

        write_json(report, report_path)
        update("Completed", 1.0)

        return {
            "video": str(output_video),
            "subtitles": str(output_srt),
            "report": str(report_path),
            "segments": results,
        }
