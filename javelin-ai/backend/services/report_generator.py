"""
report_generator.py
───────────────────
Combines the ScoredReport with Claude AI to produce a rich,
athlete-friendly natural language coaching report stored in Firestore.
"""

import json
import logging
import httpx
import os
from dataclasses import asdict
from datetime import datetime, timezone
from services.scorer import ScoredReport

logger = logging.getLogger("amentum.report")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL     = "https://api.anthropic.com/v1/messages"
MODEL             = "claude-sonnet-4-20250514"


async def generate_ai_narrative(scored: ScoredReport) -> str:
    """
    Call Claude to produce a warm, coach-like narrative summary
    based on the structured scoring data.
    """
    if not ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY – skipping AI narrative")
        return _fallback_narrative(scored)

    prompt = f"""You are an elite javelin throw biomechanics coach reviewing an AI analysis report.
Write a concise, motivating 3-paragraph coaching summary for the athlete.

Use this structured data:
{json.dumps({
    "overall_score":  scored.overall_score,
    "grade":          scored.grade,
    "release_angle":  scored.release_angle,
    "sections": [
        {{"name": s.name, "score": round(s.score,1), "issues": s.issues, "good_points": s.good_points}}
        for s in scored.sections
    ],
    "issues":          scored.issues,
    "recommendations": scored.recommendations,
    "duration_sec":    scored.duration_sec,
}, indent=2)}

Guidelines:
- Para 1: Celebrate what the athlete did well (reference specific sections/angles).
- Para 2: Clearly describe the 1-2 most critical issues to fix (be technical but approachable).
- Para 3: Provide a specific one-week training focus with concrete drill names.
- Tone: World-class coach – encouraging, precise, actionable. NO filler phrases.
- Length: 180-220 words total.
"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key":         ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      MODEL,
                    "max_tokens": 400,
                    "messages":   [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"].strip()
            logger.info("AI narrative generated (%d chars)", len(text))
            return text
    except Exception as e:
        logger.error("AI narrative failed: %s", e)
        return _fallback_narrative(scored)


def _fallback_narrative(scored: ScoredReport) -> str:
    good_sections = [s.name for s in scored.sections if s.score >= 70]
    weak_sections = [s.name for s in scored.sections if s.score < 60]

    para1 = (
        f"Your throw scored {scored.overall_score}/100 ({scored.grade}). "
        + (f"Strong performance in {', '.join(good_sections)}. " if good_sections else "")
    )
    para2 = (
        f"Key areas to address: {'; '.join(scored.issues[:2])}. " if scored.issues
        else "Technique is fundamentally sound. "
    )
    para3 = (
        f"Focus this week on: {scored.recommendations[0]}" if scored.recommendations
        else "Keep training consistently and re-upload after 2 weeks."
    )
    return f"{para1}\n\n{para2}\n\n{para3}"


async def build_full_report(scored: ScoredReport,
                             user_id: str,
                             tier: str = "free") -> dict:
    """
    Assemble the complete report document to be stored in Firestore / returned via API.
    """
    narrative = await generate_ai_narrative(scored)

    report_doc = {
        "video_id":       scored.video_id,
        "user_id":        user_id,
        "tier":           tier,                # "free" | "premium"
        "created_at":     datetime.now(timezone.utc).isoformat(),
        "overall_score":  scored.overall_score,
        "grade":          scored.grade,
        "release_angle":  scored.release_angle,
        "duration_sec":   scored.duration_sec,
        "frame_count":    scored.frame_count,

        "sections": [
            {
                "name":        s.name,
                "score":       round(s.score, 1),
                "weighted":    round(s.weighted, 1),
                "max_weight":  s.weight,
                "issues":      s.issues,
                "good_points": s.good_points,
            }
            for s in scored.sections
        ],

        "issues":          scored.issues,
        "recommendations": scored.recommendations,
        "key_angles":      scored.key_angles,
        "ai_narrative":    narrative,

        # Premium-only fields (populated later by human coach)
        "coach_notes":     None if tier == "free" else "",
        "coach_reviewed":  False,
        "iterations_used": 0,
    }

    return report_doc
