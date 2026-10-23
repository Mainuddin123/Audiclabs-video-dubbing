
import pytest

from src.evaluation import (
    evaluate_report,
    summarize_human_ratings,
)


def test_evaluate_report_uses_real_report_fields():
    report = {
        "segment_count": 2,
        "speed_adjustments": 1,
        "timing": [
            {
                "segment": 0,
                "slot_seconds": 1.0,
                "generated_seconds": 1.2,
                "duration_difference_seconds": 0.2,
                "speed": 1.2,
            },
            {
                "segment": 1,
                "slot_seconds": 2.0,
                "generated_seconds": 2.0,
                "duration_difference_seconds": 0.0,
                "speed": 1.0,
            },
        ],
    }

    result = evaluate_report(report)

    assert result["total_segments"] == 2
    assert result["segments_with_timing_metrics"] == 2
    assert result["speed_adjustments"] == 1
    assert result["speed_adjustment_percentage"] == 50.0
    assert result["mean_absolute_duration_difference_seconds"] == 0.1
    assert result["max_absolute_duration_difference_seconds"] == 0.2
    assert result["segments"][0]["speed_adjusted"] is True
    assert result["segments"][1]["speed_adjusted"] is False


def test_evaluate_report_handles_empty_timing():
    result = evaluate_report(
        {
            "segment_count": 0,
            "speed_adjustments": 0,
            "timing": [],
        }
    )

    assert result["segments"] == []
    assert result["speed_adjustment_percentage"] == 0.0
    assert result["mean_absolute_duration_difference_seconds"] == 0.0


def test_summarize_human_ratings():
    ratings = [
        {
            "clarity": "Good",
            "translation": "Good",
            "synchronization": "Acceptable",
            "background": "Good",
        },
        {
            "clarity": "Good",
            "translation": "Good",
            "synchronization": "Good",
            "background": "Good",
        },
    ]

    result = summarize_human_ratings(ratings)

    assert result["videos_rated"] == 2
    assert result["ratings"]["clarity"]["distribution"]["good"] == 2
    assert result["ratings"]["synchronization"]["count"] == 2


def test_summarize_human_ratings_empty_list():
    result = summarize_human_ratings([])

    assert result["videos_rated"] == 0
    assert result["ratings"]["clarity"]["count"] == 0
