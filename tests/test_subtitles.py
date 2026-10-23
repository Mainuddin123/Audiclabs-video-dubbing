
from pathlib import Path

from src.subtitles import _timestamp, write_srt


def test_timestamp_formats_seconds():
    assert _timestamp(65.123) == "00:01:05,123"


def test_timestamp_handles_negative_values():
    assert _timestamp(-2) == "00:00:00,000"


def test_write_srt_creates_valid_subtitle_file(tmp_path):
    output = tmp_path / "nested" / "translated.srt"

    segments = [
        {
            "start": 0,
            "end": 2.5,
            "translated_text": "Hello everyone",
        },
        {
            "start": 2.5,
            "end": 4,
            "translated_text": "Welcome back",
        },
    ]

    result = write_srt(segments, output)

    assert result == str(output)
    assert output.exists()

    content = output.read_text(encoding="utf-8")

    assert "1\n00:00:00,000 --> 00:00:02,500\nHello everyone" in content
    assert "2\n00:00:02,500 --> 00:00:04,000\nWelcome back" in content


def test_write_srt_skips_invalid_duration_and_empty_text(tmp_path):
    output = tmp_path / "filtered.srt"

    segments = [
        {
            "start": 3,
            "end": 2,
            "translated_text": "Invalid duration",
        },
        {
            "start": 1,
            "end": 2,
            "translated_text": "   ",
        },
        {
            "start": 2,
            "end": 3,
            "translated_text": "Valid subtitle",
        },
    ]

    write_srt(segments, output)
    content = output.read_text(encoding="utf-8")

    assert "Invalid duration" not in content
    assert "Valid subtitle" in content
    assert "3\n00:00:02,000 --> 00:00:03,000\nValid subtitle" in content
