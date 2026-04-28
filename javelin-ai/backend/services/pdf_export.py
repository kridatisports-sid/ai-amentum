"""
pdf_export.py
─────────────
Generates a professionally styled PDF report using ReportLab.
Produces: cover page, score summary, section breakdown, angles table,
AI narrative, and recommendations.
"""

import io
import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger("amentum.pdf")

# ── Brand colours ─────────────────────────────────────────────────────────────
BLACK    = colors.HexColor("#0A0A0A")
GOLD     = colors.HexColor("#C9A84C")
RED      = colors.HexColor("#D32F2F")
WHITE    = colors.white
LIGHT_BG = colors.HexColor("#F5F5F5")
MID_GREY = colors.HexColor("#888888")

PAGE_W, PAGE_H = A4


def _score_colour(score: float) -> colors.HexColor:
    if score >= 80: return colors.HexColor("#2E7D32")
    if score >= 60: return colors.HexColor("#F9A825")
    return RED


def _styles():
    base = getSampleStyleSheet()
    custom = {}

    custom["Title"] = ParagraphStyle(
        "Title", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=26, leading=30,
        textColor=WHITE, alignment=TA_CENTER,
    )
    custom["SubTitle"] = ParagraphStyle(
        "SubTitle", parent=base["Normal"],
        fontName="Helvetica", fontSize=12, leading=16,
        textColor=GOLD, alignment=TA_CENTER,
    )
    custom["Heading1"] = ParagraphStyle(
        "Heading1", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=16, leading=20,
        textColor=BLACK, spaceAfter=4,
    )
    custom["Heading2"] = ParagraphStyle(
        "Heading2", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=12, leading=15,
        textColor=GOLD,
    )
    custom["Body"] = ParagraphStyle(
        "Body", parent=base["Normal"],
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=BLACK, spaceAfter=4,
    )
    custom["Small"] = ParagraphStyle(
        "Small", parent=base["Normal"],
        fontName="Helvetica", fontSize=8, leading=11,
        textColor=MID_GREY,
    )
    custom["Issue"] = ParagraphStyle(
        "Issue", parent=base["Normal"],
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=RED, leftIndent=12,
    )
    custom["Good"] = ParagraphStyle(
        "Good", parent=base["Normal"],
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=colors.HexColor("#2E7D32"), leftIndent=12,
    )
    custom["Rec"] = ParagraphStyle(
        "Rec", parent=base["Normal"],
        fontName="Helvetica-Oblique", fontSize=9, leading=13,
        textColor=BLACK, leftIndent=16, spaceAfter=4,
    )
    return custom


def _cover_page(story, styles, report: dict):
    """Dark cover page with brand identity."""
    story.append(Spacer(1, 40 * mm))

    # Logo (if available)
    logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "logo.png")
    if os.path.exists(logo_path):
        story.append(RLImage(logo_path, width=50 * mm, height=25 * mm, hAlign="CENTER"))
        story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("AMENTUM SPORTS", styles["SubTitle"]))
    story.append(Spacer(1, 4 * mm))

    # Big score ring (text approximation)
    score_text = f"{report['overall_score']:.0f}"
    score_style = ParagraphStyle(
        "Score", fontName="Helvetica-Bold", fontSize=72, leading=80,
        textColor=GOLD, alignment=TA_CENTER,
    )
    story.append(Paragraph(score_text, score_style))

    grade_style = ParagraphStyle(
        "Grade", fontName="Helvetica", fontSize=18, leading=22,
        textColor=WHITE, alignment=TA_CENTER,
    )
    story.append(Paragraph(f"/ 100   ·   {report['grade'].upper()}", grade_style))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("JAVELIN THROW AI ANALYSIS", styles["Title"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"Video ID: {report['video_id']}   ·   "
        f"Generated: {datetime.fromisoformat(report['created_at']).strftime('%d %b %Y  %H:%M UTC')}",
        styles["Small"]
    ))
    story.append(PageBreak())


def _section_table(story, styles, report: dict):
    story.append(Paragraph("SECTION BREAKDOWN", styles["Heading1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))

    headers = ["Section", "Score", "/ 100", "Status"]
    data = [headers]
    for sec in report["sections"]:
        score = sec["score"]
        status = "✓ Good" if score >= 70 else ("△ Fair" if score >= 50 else "✗ Needs Work")
        data.append([
            sec["name"],
            f"{score:.0f}",
            f"(max {sec['max_weight']} pts)",
            status,
        ])

    col_widths = [75 * mm, 25 * mm, 40 * mm, 40 * mm]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), BLACK),
        ("TEXTCOLOR",   (0, 0), (-1, 0), GOLD),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("GRID",        (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6 * mm))


def _angles_table(story, styles, report: dict):
    if not report.get("key_angles"):
        return

    story.append(Paragraph("KEY ANGLES AT RELEASE", styles["Heading1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))

    LABELS = {
        "right_elbow":              "Right Elbow",
        "right_shoulder_abduction": "Shoulder Abduction",
        "arm_release_angle":        "Release Angle",
        "hip_separation":           "Hip-Shoulder Sep.",
        "trunk_lean":               "Trunk Lean",
        "right_knee":               "Block Leg (Right Knee)",
    }

    IDEALS = {
        "right_elbow":              "155–180°",
        "right_shoulder_abduction": "70–110°",
        "arm_release_angle":        "30–36°",
        "hip_separation":           "85–110°",
        "trunk_lean":               "0–20°",
        "right_knee":               "160–180°",
    }

    data = [["Angle", "Measured", "Ideal Range", "Status"]]
    for key, label in LABELS.items():
        val = report["key_angles"].get(key)
        if val is None:
            continue
        ideal = IDEALS.get(key, "—")
        # Simple OK/flag
        lo, hi = [float(x.replace("°", "")) for x in ideal.replace("–", "-").split("-")]
        status = "✓" if lo <= val <= hi else "⚠"
        data.append([label, f"{val:.1f}°", ideal, status])

    col_widths = [65 * mm, 30 * mm, 35 * mm, 20 * mm]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), BLACK),
        ("TEXTCOLOR",   (0, 0), (-1, 0), GOLD),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("GRID",        (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6 * mm))


def _issues_and_recs(story, styles, report: dict):
    story.append(Paragraph("IDENTIFIED ISSUES", styles["Heading1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=RED, spaceAfter=6))
    for issue in report.get("issues", []):
        story.append(Paragraph(f"▸ {issue}", styles["Issue"]))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("TRAINING RECOMMENDATIONS", styles["Heading1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=6))
    for i, rec in enumerate(report.get("recommendations", []), 1):
        story.append(Paragraph(f"{i}. {rec}", styles["Rec"]))
    story.append(Spacer(1, 5 * mm))


def _narrative(story, styles, report: dict):
    narrative = report.get("ai_narrative", "")
    if not narrative:
        return
    story.append(Paragraph("COACH ANALYSIS (AI-GENERATED)", styles["Heading1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))
    for para in narrative.split("\n\n"):
        story.append(Paragraph(para.strip(), styles["Body"]))
        story.append(Spacer(1, 3 * mm))


def _premium_section(story, styles, report: dict):
    if report.get("tier") != "premium":
        return
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("HUMAN COACH NOTES", styles["Heading1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))
    notes = report.get("coach_notes") or "Awaiting coach review …"
    story.append(Paragraph(notes, styles["Body"]))


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MID_GREY)
    canvas.drawCentredString(PAGE_W / 2, 12 * mm,
                             "Amentum Sports · www.amentums.com · Confidential Athlete Report")
    canvas.drawRightString(PAGE_W - 20 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf(report: dict, output_path: str) -> str:
    """
    Build a full PDF report and write it to output_path.
    Returns output_path on success.
    """
    logger.info("Generating PDF for video %s", report.get("video_id"))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm,  bottomMargin=20 * mm,
    )

    styles = _styles()
    story  = []

    _cover_page(story, styles, report)
    _section_table(story, styles, report)
    _angles_table(story, styles, report)
    _issues_and_recs(story, styles, report)
    _narrative(story, styles, report)
    _premium_section(story, styles, report)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    logger.info("PDF written to %s", output_path)
    return output_path
