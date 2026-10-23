
from typing import Any


def evaluate_report(report: dict[str, Any]) -> dict[str, Any]:
    """Summarize timing and speed-adjustment metrics from a pipeline report."""
    timing = report.get("timing", [])
    total_segments = int(report.get("segment_count", len(timing)))
    speed_adjustments = int(report.get("speed_adjustments", 0))

    segment_metrics = []

    for item in timing:
        slot = float(item.get("slot_seconds", 0))
        generated = float(item.get("generated_seconds", 0))
        difference = float(
            item.get(
                "duration_difference_seconds",
                generated - slot,
            )
        )

        segment_metrics.append(
            {
                "segment": item.get("segment"),
                "slot_seconds": round(slot, 3),
                "generated_seconds": round(generated, 3),
                "duration_difference_seconds": round(difference, 3),
                "absolute_duration_difference_seconds": round(
                    abs(difference), 3
                ),
                "speed": item.get("speed"),
                "speed_adjusted": (
                    item.get("speed") is not None
                    and abs(float(item["speed"]) - 1.0) > 0.001
                ),
            }
        )

    absolute_differences = [
        item["absolute_duration_difference_seconds"]
        for item in segment_metrics
    ]

    return {
        "total_segments": total_segments,
        "segments_with_timing_metrics": len(segment_metrics),
        "speed_adjustments": speed_adjustments,
        "speed_adjustment_percentage": round(
            speed_adjustments / total_segments * 100, 2
        ) if total_segments else 0.0,
        "mean_absolute_duration_difference_seconds": round(
            sum(absolute_differences) / len(absolute_differences), 3
        ) if absolute_differences else 0.0,
        "max_absolute_duration_difference_seconds": round(
            max(absolute_differences), 3
        ) if absolute_differences else 0.0,
        "segments": segment_metrics,
    }


def summarize_human_ratings(
    ratings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize qualitative ratings collected from human reviewers."""
    fields = ("clarity", "translation", "synchronization", "background")
    summary: dict[str, Any] = {
        "videos_rated": len(ratings),
        "ratings": {},
    }

    for field in fields:
        values = [
            str(item[field]).strip().lower()
            for item in ratings
            if item.get(field)
        ]
        summary["ratings"][field] = {
            "count": len(values),
            "distribution": {
                value: values.count(value)
                for value in sorted(set(values))
            },
        }

    return summary
