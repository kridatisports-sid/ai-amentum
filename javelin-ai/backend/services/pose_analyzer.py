"""
pose_analyzer.py
────────────────
MediaPipe-based javelin throw biomechanical analysis pipeline.

Pipeline:
  1. Extract frames from uploaded video at adaptive FPS
  2. Run MediaPipe Pose on each frame
  3. Calculate joint angles (elbow, shoulder, hip, knee, wrist)
  4. Detect throw phases (approach → crossover → power → release → follow-through)
  5. Identify the release frame (peak wrist height with forward velocity)
  6. Return structured landmarks + angle time-series
"""

import cv2
import numpy as np
import mediapipe as mp
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("amentum.pose")

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# ── Landmark indices (MediaPipe 33-point model) ───────────────────────────────
LM = mp_pose.PoseLandmark


@dataclass
class FrameAnalysis:
    frame_idx: int
    timestamp_ms: float
    landmarks: list          # raw landmark dicts
    angles: dict             # named angle → degrees
    phase: str               # detected throw phase
    visibility_score: float  # avg visibility of key points


@dataclass
class ThrowAnalysis:
    video_id: str
    fps: float
    total_frames: int
    duration_sec: float
    frame_analyses: list[FrameAnalysis] = field(default_factory=list)
    release_frame_idx: Optional[int] = None
    key_frames: dict = field(default_factory=dict)  # phase → frame_idx
    overlay_video_path: Optional[str] = None
    keyframe_paths: dict = field(default_factory=dict)


# ── Angle helpers ─────────────────────────────────────────────────────────────

def _landmark_to_np(landmark) -> np.ndarray:
    return np.array([landmark.x, landmark.y, landmark.z])


def _angle_3pts(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle at vertex B formed by rays B→A and B→C (degrees)."""
    ba = a - b
    bc = c - b
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def compute_angles(lms) -> dict:
    """
    Extract biomechanically relevant angles from a MediaPipe landmark list.
    We always use the THROWING arm side (right by convention; flip if needed).
    """
    def pt(idx):
        return _landmark_to_np(lms[idx])

    angles = {}

    # ── Throwing arm (right side) ─────────────────────────────────────────
    try:
        angles["right_elbow"] = _angle_3pts(
            pt(LM.RIGHT_SHOULDER), pt(LM.RIGHT_ELBOW), pt(LM.RIGHT_WRIST)
        )
        angles["right_shoulder_abduction"] = _angle_3pts(
            pt(LM.RIGHT_HIP), pt(LM.RIGHT_SHOULDER), pt(LM.RIGHT_ELBOW)
        )
        angles["right_shoulder_elevation"] = _angle_3pts(
            pt(LM.RIGHT_ELBOW), pt(LM.RIGHT_SHOULDER), pt(LM.LEFT_SHOULDER)
        )
        angles["right_wrist_extension"] = _angle_3pts(
            pt(LM.RIGHT_ELBOW), pt(LM.RIGHT_WRIST), pt(LM.RIGHT_INDEX)
        )
    except Exception as e:
        logger.debug("Arm angle error: %s", e)

    # ── Hips ──────────────────────────────────────────────────────────────
    try:
        angles["hip_separation"] = _angle_3pts(
            pt(LM.LEFT_HIP), pt(LM.RIGHT_HIP), pt(LM.RIGHT_SHOULDER)
        )
        angles["right_hip_flexion"] = _angle_3pts(
            pt(LM.RIGHT_SHOULDER), pt(LM.RIGHT_HIP), pt(LM.RIGHT_KNEE)
        )
        angles["left_hip_flexion"] = _angle_3pts(
            pt(LM.LEFT_SHOULDER), pt(LM.LEFT_HIP), pt(LM.LEFT_KNEE)
        )
    except Exception as e:
        logger.debug("Hip angle error: %s", e)

    # ── Knees ─────────────────────────────────────────────────────────────
    try:
        angles["right_knee"] = _angle_3pts(
            pt(LM.RIGHT_HIP), pt(LM.RIGHT_KNEE), pt(LM.RIGHT_ANKLE)
        )
        angles["left_knee"] = _angle_3pts(
            pt(LM.LEFT_HIP), pt(LM.LEFT_KNEE), pt(LM.LEFT_ANKLE)
        )
    except Exception as e:
        logger.debug("Knee angle error: %s", e)

    # ── Trunk lean (angle of torso from vertical) ─────────────────────────
    try:
        mid_hip = (pt(LM.LEFT_HIP) + pt(LM.RIGHT_HIP)) / 2
        mid_shoulder = (pt(LM.LEFT_SHOULDER) + pt(LM.RIGHT_SHOULDER)) / 2
        torso_vec = mid_shoulder - mid_hip
        vertical = np.array([0, -1, 0])
        cos_a = np.dot(torso_vec[:2], vertical[:2]) / (
            np.linalg.norm(torso_vec[:2]) + 1e-9
        )
        angles["trunk_lean"] = float(np.degrees(np.arccos(np.clip(cos_a, -1, 1))))
    except Exception as e:
        logger.debug("Trunk lean error: %s", e)

    # ── Release angle: angle between arm vector and horizontal ────────────
    try:
        shoulder = pt(LM.RIGHT_SHOULDER)
        wrist = pt(LM.RIGHT_WRIST)
        arm_vec = wrist - shoulder
        horiz = np.array([1, 0, 0])
        cos_r = np.dot(arm_vec[:2], horiz[:2]) / (
            np.linalg.norm(arm_vec[:2]) + 1e-9
        )
        angles["arm_release_angle"] = float(
            np.degrees(np.arccos(np.clip(abs(cos_r), 0, 1)))
        )
    except Exception as e:
        logger.debug("Release angle error: %s", e)

    return angles


# ── Phase detection ───────────────────────────────────────────────────────────

def detect_phase(frame_idx: int, total: int, angles: dict) -> str:
    """
    Heuristic phase assignment based on normalised position + joint angles.
    In a full production system this would be a trained sequence classifier.
    """
    ratio = frame_idx / max(total - 1, 1)
    elbow = angles.get("right_elbow", 180)
    hip   = angles.get("hip_separation", 90)

    if ratio < 0.25:
        return "approach"
    elif ratio < 0.45:
        return "crossover"
    elif ratio < 0.60:
        return "power_position"
    elif ratio < 0.75:
        # Elbow coming through; hip–shoulder separation peaking
        if elbow < 160 or hip > 100:
            return "release"
        return "power_position"
    elif ratio < 0.90:
        return "follow_through"
    else:
        return "recovery"


# ── Release frame detection ───────────────────────────────────────────────────

def find_release_frame(frame_analyses: list[FrameAnalysis]) -> int:
    """
    Find the most likely release frame:
    - Wrist is at its highest Y coordinate (lowest pixel value)
    - Phase is 'release'
    Falls back to first 'release' phase frame.
    """
    release_frames = [f for f in frame_analyses if f.phase == "release"]
    if not release_frames:
        # Fallback: frame with highest wrist position (lowest y normalised)
        best = min(frame_analyses,
                   key=lambda f: f.landmarks[LM.RIGHT_WRIST]["y"]
                   if len(f.landmarks) > LM.RIGHT_WRIST else 999)
        return best.frame_idx

    # Among release frames, pick peak wrist height
    def wrist_y(fa):
        try:
            return fa.landmarks[LM.RIGHT_WRIST]["y"]
        except Exception:
            return 999.0

    best = min(release_frames, key=wrist_y)
    return best.frame_idx


# ── Overlay drawing ───────────────────────────────────────────────────────────

def draw_overlay(frame: np.ndarray, result, angles: dict, phase: str) -> np.ndarray:
    """Draw pose skeleton + angle annotations on a frame."""
    annotated = frame.copy()

    if result.pose_landmarks:
        mp_drawing.draw_landmarks(
            annotated,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style(),
        )

    h, w = annotated.shape[:2]

    # Phase badge
    phase_color = {
        "approach":       (255, 200,   0),
        "crossover":      (255, 140,   0),
        "power_position": (255,  50,  50),
        "release":        (50,  255,  50),
        "follow_through": (50,  180, 255),
        "recovery":       (200, 200, 200),
    }.get(phase, (255, 255, 255))

    cv2.rectangle(annotated, (10, 10), (280, 40), (0, 0, 0), -1)
    cv2.putText(annotated, f"Phase: {phase.replace('_', ' ').title()}",
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, phase_color, 2)

    # Key angle readouts
    y = 70
    for name, value in angles.items():
        if name in ("right_elbow", "right_shoulder_abduction", "arm_release_angle",
                    "hip_separation", "trunk_lean"):
            label = name.replace("_", " ").title()
            cv2.rectangle(annotated, (10, y - 18), (260, y + 6), (0, 0, 0), -1)
            cv2.putText(annotated, f"{label}: {value:.1f}°",
                        (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            y += 28

    return annotated


# ── Main analysis entry point ─────────────────────────────────────────────────

def analyze_video(video_path: str, video_id: str,
                  sample_fps: float = 10.0) -> ThrowAnalysis:
    """
    Run the full analysis pipeline on a local video file.

    Args:
        video_path:  Local path to the uploaded video.
        video_id:    Unique identifier for this analysis job.
        sample_fps:  How many frames per second to analyse (default 10).
                     Higher = more accurate but slower.

    Returns:
        ThrowAnalysis dataclass with all results.
    """
    logger.info("Analysing video %s  path=%s", video_id, video_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    native_fps   = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / native_fps

    # Determine frame sampling stride
    stride = max(1, int(native_fps / sample_fps))
    logger.info("native_fps=%.1f  total=%d  stride=%d  duration=%.1fs",
                native_fps, total_frames, stride, duration_sec)

    result = ThrowAnalysis(
        video_id=video_id,
        fps=native_fps,
        total_frames=total_frames,
        duration_sec=duration_sec,
    )

    # Overlay video writer
    overlay_path = f"tmp/outputs/{video_id}_overlay.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(overlay_path, fourcc, native_fps, (width, height))

    frame_analyses: list[FrameAnalysis] = []
    frame_idx = 0

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,           # most accurate
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            should_analyse = (frame_idx % stride == 0)

            if should_analyse:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pose_result = pose.process(rgb)

                angles: dict = {}
                landmarks_list = []
                vis_score = 0.0

                if pose_result.pose_landmarks:
                    lms = pose_result.pose_landmarks.landmark
                    angles = compute_angles(lms)

                    # Serialise landmarks to plain dicts
                    for lm in lms:
                        landmarks_list.append(
                            {"x": lm.x, "y": lm.y, "z": lm.z,
                             "visibility": lm.visibility}
                        )

                    KEY_LMS = [
                        LM.RIGHT_SHOULDER, LM.LEFT_SHOULDER,
                        LM.RIGHT_ELBOW,    LM.RIGHT_WRIST,
                        LM.RIGHT_HIP,      LM.LEFT_HIP,
                        LM.RIGHT_KNEE,     LM.LEFT_KNEE,
                    ]
                    vis_score = np.mean([lms[k].visibility for k in KEY_LMS])

                phase = detect_phase(frame_idx, total_frames, angles)

                fa = FrameAnalysis(
                    frame_idx=frame_idx,
                    timestamp_ms=frame_idx / native_fps * 1000,
                    landmarks=landmarks_list,
                    angles=angles,
                    phase=phase,
                    visibility_score=float(vis_score),
                )
                frame_analyses.append(fa)

                # Draw overlay frame
                overlay_frame = draw_overlay(frame, pose_result, angles, phase)
                writer.write(overlay_frame)
            else:
                # Write original frame (not analysed) to keep video timing
                writer.write(frame)

            frame_idx += 1

    cap.release()
    writer.release()

    result.frame_analyses    = frame_analyses
    result.overlay_video_path = overlay_path

    if frame_analyses:
        result.release_frame_idx = find_release_frame(frame_analyses)

    # Save key frames (one per phase) as JPEGs
    _save_keyframes(video_path, result)

    logger.info("Analysis done. %d frames analysed. Release frame: %s",
                len(frame_analyses), result.release_frame_idx)
    return result


def _save_keyframes(video_path: str, result: ThrowAnalysis):
    """Extract one representative frame per phase and save as JPEG."""
    phase_order = ["approach", "crossover", "power_position",
                   "release", "follow_through", "recovery"]
    phase_frames: dict[str, int] = {}
    for fa in result.frame_analyses:
        if fa.phase not in phase_frames:
            phase_frames[fa.phase] = fa.frame_idx

    cap = cv2.VideoCapture(video_path)
    paths: dict[str, str] = {}

    for phase in phase_order:
        if phase not in phase_frames:
            continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, phase_frames[phase])
        ret, frame = cap.read()
        if not ret:
            continue
        save_path = f"tmp/outputs/{result.video_id}_kf_{phase}.jpg"
        cv2.imwrite(save_path, frame)
        paths[phase] = save_path

    cap.release()
    result.keyframe_paths = paths
    # Also store key frame indices for the report
    result.key_frames = phase_frames
