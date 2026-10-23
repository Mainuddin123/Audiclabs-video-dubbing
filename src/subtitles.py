
from pathlib import Path


def _timestamp(seconds):
    milliseconds = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def write_srt(segments, output_path):
    """Write translated segments to a standard SRT subtitle file."""
    lines = []

    for index, segment in enumerate(segments, start=1):
        start = float(segment["start"])
        end = float(segment["end"])

        if end <= start:
            continue

        text = str(segment.get("translated_text", "")).strip()
        if not text:
            continue

        lines.extend([
            str(index),
            f"{_timestamp(start)} --> {_timestamp(end)}",
            text,
            "",
        ])

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
