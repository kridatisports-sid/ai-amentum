"""
scorer.py
─────────
Converts raw ThrowAnalysis data into a structured scoring report.

Scoring model (total 100 pts):
  ┌───────────────────────┬────────┐
  │ Section               │ Weight │
  ├───────────────────────┼────────┤
  │ Approach              │  15 pts│
  │ Crossover / Transition│  20 pts│
  │ Power Position        │  20 pts│
  │ Release               │  30 pts│
  │ Follow-Through        │  15 pts│
  └───────────────────────┴────────┘

Each section is scored from its relevant frame window using
biomechanical thresholds derived from IAAF coaching literature.
"""

import statistics
import logging
from dataclasses import dataclass, field
from typing import Optional
from services.pose_analyzer import ThrowAnalysis, FrameAnalysis

logger = logging.getLogger("amentum.scorer")

# ── Ideal angle ranges from biomechanics literature ──────────────────────────
IDEAL = {
    "right_elbow":               (155, 180),   # extended but not locked
    "right_shoulder_abduction":  (70,  110),   # arm up and back
    "arm_release_angle":         (30,  36),    # classic ~33° release
    "hip_separation":            (85,  110),   # torso rotation
    "trunk_lean":                (0,   20),    # upright at release
    "right_knee":                (160, 180),   # block leg nearly straight
    "left_knee":                 (110, 160),   # drive knee bent but not collapsed
}

# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SectionScore:
    name: str
    score: float            # 0–100 within section
    weighted: float         # contribution to overall
    weight: int             # max pts for section
    issues: list[str]       # identified problems
    good_points: list[str]  # positive observations


@dataclass
class ScoredReport:
    video_id: str
    overall_score: float
    grade: str
    sections: list[SectionScore]
    issues: list[str]
    recommendations: list[str]
    release_angle: Optional[float]
    key_angles: dict          # angle name → value at release frame
    angle_timeseries: dict    # angle name → [values over time]
    frame_count: int
    duration_sec: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def _frames_in_phase(analyses: list[FrameAnalysis], phase: str) -> list[FrameAnalysis]:
    return [f for f in analyses if f.phase == phase]


def _avg_angle(frames: list[FrameAnalysis], key: str) -> Optional[float]:
    vals = [f.angles[key] for f in frames if key in f.angles]
    return statistics.mean(vals) if vals else None


def _score_angle(value: Optional[float], ideal_min: float, ideal_max: float,
                 tolerance: float = 15.0) -> float:
    """
    Return 0-100 score based on how close value is to [ideal_min, ideal_max].
    tolerance defines the outer boundary at which score → 0.
    """
    if value is None:
        return 50.0   # neutral if not detected

    ideal_centre = (ideal_min + ideal_max) / 2
    half_range   = (ideal_max - ideal_min) / 2

    if ideal_min <= value <= ideal_max:
        return 100.0

    dist = min(abs(value - ideal_min), abs(value - ideal_max))
    score = max(0.0, 100.0 - (dist / tolerance) * 100.0)
    return round(score, 1)


def _grade(score: float) -> str:
    if score >= 90: return "Elite"
    if score >= 75: return "Advanced"
    if score >= 60: return "Intermediate"
    if score >= 45: return "Developing"
    return "Beginner"


# ── Section scorers ───────────────────────────────────────────────────────────

def _score_approach(frames: list[FrameAnalysis]) -> SectionScore:
    WEIGHT = 15
    issues, good = [], []
    sub_scores = []

    trunk_avg = _avg_angle(frames, "trunk_lean")
    if trunk_avg is not None:
        s = _score_angle(trunk_avg, 0, 20, 20)
        sub_scores.append(s)
        if trunk_avg > 25:
            issues.append(f"Excessive trunk lean during approach ({trunk_avg:.0f}°; ideal <20°).")
        elif trunk_avg <= 20:
            good.append("Good upright posture maintained in approach.")

    hip_avg = _avg_angle(frames, "right_hip_flexion")
    if hip_avg is not None:
        s = _score_angle(hip_avg, 150, 180, 30)
        sub_scores.append(s)
        if hip_avg < 140:
            issues.append("Hips dropping during approach – maintain hip drive.")
        else:
            good.append("Strong hip extension through approach.")

    # Visibility of key landmarks → confidence in analysis
    vis = statistics.mean([f.visibility_score for f in frames]) if frames else 0
    if vis < 0.5:
        issues.append("Low pose detection confidence during approach – check camera angle.")

    raw = statistics.mean(sub_scores) if sub_scores else 65.0
    weighted = (raw / 100) * WEIGHT
    return SectionScore("Approach", raw, weighted, WEIGHT, issues, good)


def _score_crossover(frames: list[FrameAnalysis]) -> SectionScore:
    WEIGHT = 20
    issues, good = [], []
    sub_scores = []

    knee_avg = _avg_angle(frames, "right_knee")
    if knee_avg is not None:
        s = _score_angle(knee_avg, 110, 150, 30)
        sub_scores.append(s)
        if knee_avg > 160:
            issues.append(f"Knee too straight in crossover ({knee_avg:.0f}°) – absorb with flexion.")
        elif knee_avg < 100:
            issues.append(f"Excessive knee collapse in crossover ({knee_avg:.0f}°).")
        else:
            good.append("Good crossover knee drive.")

    hip_sep = _avg_angle(frames, "hip_separation")
    if hip_sep is not None:
        s = _score_angle(hip_sep, 85, 110, 25)
        sub_scores.append(s)
        if hip_sep < 70:
            issues.append("Insufficient hip-shoulder separation during crossover.")
        else:
            good.append("Hip-shoulder separation building well.")

    raw = statistics.mean(sub_scores) if sub_scores else 65.0
    weighted = (raw / 100) * WEIGHT
    return SectionScore("Crossover", raw, weighted, WEIGHT, issues, good)


def _score_power_position(frames: list[FrameAnalysis]) -> SectionScore:
    WEIGHT = 20
    issues, good = [], []
    sub_scores = []

    shoulder_abd = _avg_angle(frames, "right_shoulder_abduction")
    if shoulder_abd is not None:
        s = _score_angle(shoulder_abd, 70, 110, 30)
        sub_scores.append(s)
        if shoulder_abd < 60:
            issues.append(f"Arm not pulled back sufficiently ({shoulder_abd:.0f}°) – wider draw back needed.")
        elif shoulder_abd > 120:
            issues.append(f"Over-abducted shoulder ({shoulder_abd:.0f}°) – risk of injury.")
        else:
            good.append("Good shoulder draw-back in power position.")

    elbow_avg = _avg_angle(frames, "right_elbow")
    if elbow_avg is not None:
        s = _score_angle(elbow_avg, 155, 180, 25)
        sub_scores.append(s)
        if elbow_avg < 140:
            issues.append(f"Elbow dropping at power position ({elbow_avg:.0f}°) – keep arm extended.")
        else:
            good.append("Arm extension well maintained.")

    hip_sep = _avg_angle(frames, "hip_separation")
    if hip_sep is not None:
        s = _score_angle(hip_sep, 85, 115, 30)
        sub_scores.append(s)
        if hip_sep < 75:
            issues.append("Insufficient hip-shoulder separation at power position – rotate torso more.")
        else:
            good.append("Strong hip-shoulder separation achieved.")

    raw = statistics.mean(sub_scores) if sub_scores else 65.0
    weighted = (raw / 100) * WEIGHT
    return SectionScore("Power Position", raw, weighted, WEIGHT, issues, good)


def _score_release(frames: list[FrameAnalysis],
                   release_frame: Optional[FrameAnalysis]) -> tuple[SectionScore, Optional[float]]:
    WEIGHT = 30
    issues, good = [], []
    sub_scores = []

    ref = release_frame or (frames[-1] if frames else None)
    release_angle = None

    if ref:
        # Release angle (arm vs horizontal)
        ra = ref.angles.get("arm_release_angle")
        if ra is not None:
            release_angle = ra
            s = _score_angle(ra, 30, 36, 15)
            sub_scores.append(s)
            if ra < 25:
                issues.append(f"Release angle too flat ({ra:.0f}°) – aim for 30–36°.")
            elif ra > 42:
                issues.append(f"Release angle too steep ({ra:.0f}°) – aim for 30–36°.")
            else:
                good.append(f"Release angle excellent ({ra:.0f}°).")

        # Elbow at release
        elbow_r = ref.angles.get("right_elbow")
        if elbow_r is not None:
            s = _score_angle(elbow_r, 155, 180, 25)
            sub_scores.append(s)
            if elbow_r < 145:
                issues.append(f"Elbow dropping at release ({elbow_r:.0f}°) – major power loss.")
            else:
                good.append("Good elbow extension at release.")

        # Trunk lean at release
        trunk_r = ref.angles.get("trunk_lean")
        if trunk_r is not None:
            s = _score_angle(trunk_r, 0, 20, 25)
            sub_scores.append(s)
            if trunk_r > 30:
                issues.append(f"Excessive trunk forward lean at release ({trunk_r:.0f}°).")
            else:
                good.append("Balanced trunk position at release.")

        # Block leg (right knee)
        knee_r = ref.angles.get("right_knee")
        if knee_r is not None:
            s = _score_angle(knee_r, 155, 180, 25)
            sub_scores.append(s)
            if knee_r < 140:
                issues.append(f"Block leg collapsing at release ({knee_r:.0f}°) – stiffen block leg.")
            else:
                good.append("Strong block leg at release.")

    raw = statistics.mean(sub_scores) if sub_scores else 60.0
    weighted = (raw / 100) * WEIGHT
    return SectionScore("Release", raw, weighted, WEIGHT, issues, good), release_angle


def _score_follow_through(frames: list[FrameAnalysis]) -> SectionScore:
    WEIGHT = 15
    issues, good = [], []
    sub_scores = []

    trunk_avg = _avg_angle(frames, "trunk_lean")
    if trunk_avg is not None:
        s = _score_angle(trunk_avg, 0, 30, 25)
        sub_scores.append(s)
        if trunk_avg > 40:
            issues.append("Poor balance in follow-through – trunk pitching too far forward.")
        else:
            good.append("Balanced deceleration in follow-through.")

    left_knee = _avg_angle(frames, "left_knee")
    if left_knee is not None:
        s = _score_angle(left_knee, 120, 160, 30)
        sub_scores.append(s)
        if left_knee < 100:
            issues.append("Excessive flexion in landing leg – affects balance post-release.")
        else:
            good.append("Good recovery leg position.")

    raw = statistics.mean(sub_scores) if sub_scores else 65.0
    weighted = (raw / 100) * WEIGHT
    return SectionScore("Follow-Through", raw, weighted, WEIGHT, issues, good)


# ── Angle time-series extraction ──────────────────────────────────────────────

def build_timeseries(analyses: list[FrameAnalysis]) -> dict:
    angle_keys = set()
    for fa in analyses:
        angle_keys.update(fa.angles.keys())

    ts = {k: [] for k in angle_keys}
    for fa in analyses:
        for k in angle_keys:
            ts[k].append(fa.angles.get(k))  # None if not detected that frame

    return ts


# ── Main scorer ───────────────────────────────────────────────────────────────

def score_throw(analysis: ThrowAnalysis) -> ScoredReport:
    """Convert a ThrowAnalysis into a fully scored ScoredReport."""
    fas = analysis.frame_analyses
    if not fas:
        raise ValueError("No frame analyses to score.")

    approach_f      = _frames_in_phase(fas, "approach")
    crossover_f     = _frames_in_phase(fas, "crossover")
    power_f         = _frames_in_phase(fas, "power_position")
    release_f       = _frames_in_phase(fas, "release")
    followthrough_f = _frames_in_phase(fas, "follow_through")

    # Locate release FrameAnalysis object
    release_fa = None
    if analysis.release_frame_idx is not None:
        matches = [f for f in fas if f.frame_idx == analysis.release_frame_idx]
        if matches:
            release_fa = matches[0]

    s_approach  = _score_approach(approach_f or fas[:max(1, len(fas)//5)])
    s_crossover = _score_crossover(crossover_f or fas[:max(1, len(fas)//3)])
    s_power     = _score_power_position(power_f or fas[len(fas)//3: len(fas)//2])
    s_release, release_angle = _score_release(release_f or [release_fa] if release_fa else fas, release_fa)
    s_follow    = _score_follow_through(followthrough_f or fas[-max(1, len(fas)//5):])

    sections = [s_approach, s_crossover, s_power, s_release, s_follow]
    overall  = sum(s.weighted for s in sections)

    # Aggregate issues and recommendations
    all_issues = []
    for s in sections:
        all_issues.extend(s.issues)

    recommendations = _generate_recommendations(all_issues, release_angle)

    # Key angles at release frame (or best available)
    key_angles: dict = {}
    if release_fa:
        key_angles = release_fa.angles
    elif fas:
        key_angles = fas[len(fas) // 2].angles

    timeseries = build_timeseries(fas)

    report = ScoredReport(
        video_id        = analysis.video_id,
        overall_score   = round(overall, 1),
        grade           = _grade(overall),
        sections        = sections,
        issues          = all_issues,
        recommendations = recommendations,
        release_angle   = round(release_angle, 1) if release_angle is not None else None,
        key_angles      = {k: round(v, 1) for k, v in key_angles.items()},
        angle_timeseries= timeseries,
        frame_count     = len(fas),
        duration_sec    = analysis.duration_sec,
    )

    logger.info("Scored video %s → %.1f (%s)", analysis.video_id, overall, report.grade)
    return report


def _generate_recommendations(issues: list[str], release_angle: Optional[float]) -> list[str]:
    """Map detected issues to actionable coaching cues."""
    recs = []

    issue_text = " ".join(issues).lower()

    if "elbow dropping" in issue_text:
        recs.append("Drill: 'Elbow high' wall throws – stand 1 m from a wall and release the javelin keeping elbow above shoulder line throughout.")

    if "release angle" in issue_text and release_angle is not None:
        if release_angle < 30:
            recs.append("Focus on a steeper upward wrist flick at release; target 30–36° trajectory angle.")
        elif release_angle > 38:
            recs.append("Lower the release point slightly; a steeper angle reduces range – drive forward more at release.")

    if "hip" in issue_text and "separation" in issue_text:
        recs.append("Hip-shoulder separation drill: practise slow crossover steps keeping hips forward while holding shoulders back ('bow-and-arrow' tension).")

    if "block leg" in issue_text or "collapsing" in issue_text:
        recs.append("Single-leg block drill: step into the block leg position and hold for 3 seconds – build strength to resist collapse on impact.")

    if "trunk" in issue_text and "lean" in issue_text:
        recs.append("Core stability work: planks and Pallof press to keep trunk upright through the release.")

    if "approach" in issue_text and "posture" in issue_text:
        recs.append("Approach rhythm drill: mark five run-up strides and focus on tall posture with relaxed arm carry for the first three steps.")

    if not recs:
        recs.append("Maintain current technique – focus on consistency through volume training.")
        recs.append("Video each session to track gradual improvement across all phases.")

    return recs
