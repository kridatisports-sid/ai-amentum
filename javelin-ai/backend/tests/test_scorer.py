"""
tests/test_scorer.py
Tests for the biomechanical scoring engine.
"""

import pytest
from unittest.mock import MagicMock
from services.scorer import (
    score_throw, _score_angle, _grade, ScoredReport
)
from services.pose_analyzer import ThrowAnalysis, FrameAnalysis


def _make_frame(idx, phase, angles):
    return FrameAnalysis(
        frame_idx=idx,
        timestamp_ms=idx * 100,
        landmarks=[],
        angles=angles,
        phase=phase,
        visibility_score=0.9,
    )


def _make_analysis(phases_angles: list) -> ThrowAnalysis:
    total = len(phases_angles)
    frames = [_make_frame(i, p, a) for i, (p, a) in enumerate(phases_angles)]
    return ThrowAnalysis(
        video_id="test-001",
        fps=30.0,
        total_frames=total,
        duration_sec=total / 30,
        frame_analyses=frames,
        release_frame_idx=next(
            (i for i, (p, _) in enumerate(phases_angles) if p == "release"), None
        ),
    )


GOOD_THROW = [
    ("approach",       {"trunk_lean": 10, "right_hip_flexion": 165}),
    ("approach",       {"trunk_lean": 12, "right_hip_flexion": 168}),
    ("crossover",      {"right_knee": 130, "hip_separation": 95}),
    ("crossover",      {"right_knee": 125, "hip_separation": 100}),
    ("power_position", {"right_shoulder_abduction": 90, "right_elbow": 170, "hip_separation": 105}),
    ("release",        {"arm_release_angle": 33, "right_elbow": 172, "trunk_lean": 15, "right_knee": 170}),
    ("follow_through", {"trunk_lean": 25, "left_knee": 140}),
]

BAD_THROW = [
    ("approach",       {"trunk_lean": 35, "right_hip_flexion": 130}),
    ("crossover",      {"right_knee": 95, "hip_separation": 60}),
    ("power_position", {"right_shoulder_abduction": 50, "right_elbow": 130, "hip_separation": 65}),
    ("release",        {"arm_release_angle": 20, "right_elbow": 120, "trunk_lean": 40, "right_knee": 120}),
    ("follow_through", {"trunk_lean": 50, "left_knee": 90}),
]


def test_good_throw_high_score():
    report = score_throw(_make_analysis(GOOD_THROW))
    assert report.overall_score >= 60, f"Good throw scored too low: {report.overall_score}"


def test_bad_throw_lower_score():
    bad  = score_throw(_make_analysis(BAD_THROW))
    good = score_throw(_make_analysis(GOOD_THROW))
    assert bad.overall_score < good.overall_score, "Bad throw should score lower than good throw"


def test_report_has_all_sections():
    report = score_throw(_make_analysis(GOOD_THROW))
    names  = [s.name for s in report.sections]
    for expected in ["Approach", "Crossover", "Power Position", "Release", "Follow-Through"]:
        assert expected in names


def test_release_angle_extracted():
    report = score_throw(_make_analysis(GOOD_THROW))
    assert report.release_angle is not None
    assert 28 <= report.release_angle <= 38


def test_score_angle_helper():
    assert _score_angle(33, 30, 36) == 100.0   # in range
    assert _score_angle(20, 30, 36, 15) < 50   # way outside
    assert _score_angle(None, 30, 36) == 50.0  # missing → neutral


def test_grade_labels():
    assert _grade(95)  == "Elite"
    assert _grade(78)  == "Advanced"
    assert _grade(62)  == "Intermediate"
    assert _grade(47)  == "Developing"
    assert _grade(30)  == "Beginner"


def test_issues_generated_for_bad_throw():
    report = score_throw(_make_analysis(BAD_THROW))
    assert len(report.issues) > 0, "Bad throw should produce issues"


def test_recommendations_generated():
    report = score_throw(_make_analysis(BAD_THROW))
    assert len(report.recommendations) > 0
