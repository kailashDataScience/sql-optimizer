import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "generated")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Color palette ──────────────────────────────────────────────────────────────
C_BLUE      = colors.HexColor("#2563eb")
C_GREEN     = colors.HexColor("#16a34a")
C_AMBER     = colors.HexColor("#d97706")
C_RED       = colors.HexColor("#dc2626")
C_LIGHT_BG  = colors.HexColor("#f8f9fb")
C_BORDER    = colors.HexColor("#e2e8f0")
C_TEXT      = colors.HexColor("#1e2535")
C_MUTED     = colors.HexColor("#6b7589")


def build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontSize=22, textColor=C_BLUE, spaceAfter=4,
                                fontName="Helvetica-Bold", leading=26),
        "h1": ParagraphStyle("h1", fontSize=14, textColor=C_TEXT, spaceBefore=16, spaceAfter=6,
                              fontName="Helvetica-Bold", leading=18),
        "h2": ParagraphStyle("h2", fontSize=11, textColor=C_MUTED, spaceBefore=10, spaceAfter=4,
                              fontName="Helvetica-Bold", leading=14),
        "body": ParagraphStyle("body", fontSize=10, textColor=C_TEXT, spaceAfter=4,
                               fontName="Helvetica", leading=14),
        "code": ParagraphStyle("code", fontSize=8.5, textColor=colors.HexColor("#1e40af"),
                               fontName="Courier", leading=13, backColor=colors.HexColor("#eff4ff"),
                               borderPadding=(6, 8, 6, 8), spaceAfter=8),
        "center": ParagraphStyle("center", fontSize=10, alignment=TA_CENTER,
                                 fontName="Helvetica", textColor=C_MUTED),
    }


def severity_color(sev: str) -> colors.Color:
    return {"critical": C_RED, "warning": C_AMBER, "info": C_BLUE}.get(sev.lower(), C_MUTED)


def safety_color(status: str) -> colors.Color:
    return {"SAFE": C_GREEN, "WARNING": C_AMBER, "NOT SAFE": C_RED}.get(status, C_MUTED)


def score_color(score: int) -> colors.Color:
    if score >= 80: return C_GREEN
    if score >= 60: return C_AMBER
    return C_RED


def generate_report(result: dict) -> str:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"sql_report_{ts}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    S = build_styles()
    story = []

    # ── COVER ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("QueryLens", S["title"]))
    story.append(Paragraph("SQL Query Optimization Report", ParagraphStyle(
        "sub", fontSize=13, textColor=C_MUTED, fontName="Helvetica", spaceAfter=2)))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%B %d, %Y %H:%M UTC')} &nbsp;|&nbsp; "
        f"Engine: {result.get('db_type', 'N/A').upper()}",
        ParagraphStyle("meta", fontSize=9, textColor=C_MUTED, fontName="Helvetica", spaceAfter=10)
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=16))

    # ── 1. OVERVIEW ────────────────────────────────────────────────────────────
    score = result.get("score", 0)
    safety_status = result.get("safety", {}).get("status", "UNKNOWN")
    issues = result.get("issues", [])

    story.append(Paragraph("1. Overview", S["h1"]))
    overview_data = [
        ["Metric", "Value"],
        ["Performance Score", f"{score} / 100"],
        ["Production Safety", safety_status],
        ["Issues Found", str(len(issues))],
        ["Database Engine", result.get("db_type", "N/A").upper()],
        ["Rows Scanned (est.)", result.get("rows_scanned", "N/A")],
        ["Index Usage", result.get("index_usage", "N/A")],
    ]
    tbl = Table(overview_data, colWidths=[8*cm, 9*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_BLUE),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_LIGHT_BG, colors.white]),
        ("GRID",       (0,0), (-1,-1), 0.5, C_BORDER),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("TEXTCOLOR", (1,2), (1,2), safety_color(safety_status)),
        ("TEXTCOLOR", (1,1), (1,1), score_color(score)),
        ("FONTNAME",  (1,1), (1,2), "Helvetica-Bold"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── 2. ORIGINAL QUERY ──────────────────────────────────────────────────────
    story.append(Paragraph("2. Original Query", S["h1"]))
    story.append(Paragraph(result.get("original_query", "N/A"), S["code"]))

    # ── 3. ISSUES IDENTIFIED ───────────────────────────────────────────────────
    story.append(Paragraph("3. Issues Identified", S["h1"]))
    if issues:
        issue_data = [["Severity", "Code", "Description"]]
        for i in issues:
            issue_data.append([
                i.get("severity", "").upper(),
                i.get("code", ""),
                Paragraph(i.get("description", ""), S["body"])
            ])
        tbl2 = Table(issue_data, colWidths=[2.5*cm, 4*cm, 10.5*cm])
        tbl2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), C_TEXT),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8.5),
            ("GRID",       (0,0), (-1,-1), 0.4, C_BORDER),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_LIGHT_BG, colors.white]),
            ("LEFTPADDING", (0,0), (-1,-1), 7),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ]))
        story.append(tbl2)
    else:
        story.append(Paragraph("No issues found. Query is well optimized.", S["body"]))
    story.append(Spacer(1, 0.4*cm))

    # ── 4. OPTIMIZED QUERY ─────────────────────────────────────────────────────
    story.append(Paragraph("4. Optimized Query", S["h1"]))
    story.append(Paragraph(result.get("optimized_sql", "N/A"), S["code"]))

    # ── 5. OPTIMIZATION SUGGESTIONS ───────────────────────────────────────────
    suggestions = result.get("suggestions", [])
    if suggestions:
        story.append(Paragraph("5. Optimization Suggestions", S["h1"]))
        for idx, s in enumerate(suggestions, 1):
            story.append(Paragraph(
                f"<b>{idx}. {s.get('title', '')}</b> — {s.get('detail', '')}",
                S["body"]
            ))

    story.append(PageBreak())

    # ── 6. PERFORMANCE COMPARISON ──────────────────────────────────────────────
    story.append(Paragraph("6. Performance Comparison", S["h1"]))
    before = result.get("before_metrics", {})
    after  = result.get("after_metrics", {})
    if before and after:
        comp_data = [
            ["Metric", "Before", "After"],
            ["Rows Scanned", str(before.get("rows_scanned","N/A")), str(after.get("rows_scanned","N/A"))],
            ["Est. Cost", str(before.get("estimated_cost","N/A")), str(after.get("estimated_cost","N/A"))],
            ["JOIN Count", str(before.get("join_count","N/A")), str(after.get("join_count","N/A"))],
            ["Index Usage", str(before.get("index_usage","N/A")), str(after.get("index_usage","N/A"))],
        ]
        tbl3 = Table(comp_data, colWidths=[6*cm, 6*cm, 5*cm])
        tbl3.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), C_TEXT),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("GRID",       (0,0), (-1,-1), 0.4, C_BORDER),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_LIGHT_BG, colors.white]),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING",  (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
            ("TEXTCOLOR", (2,1), (2,-1), C_GREEN),
        ]))
        story.append(tbl3)
    story.append(Spacer(1, 0.4*cm))

    # ── 7. EXECUTION PLAN ─────────────────────────────────────────────────────
    exec_plan = result.get("exec_plan", [])
    if exec_plan:
        story.append(Paragraph("7. Execution Plan Summary", S["h1"]))
        for step in exec_plan:
            t = step.get("type", "step").upper()
            d = step.get("description", "")
            story.append(Paragraph(f"<b>[{t}]</b> {d}", S["body"]))

    story.append(Spacer(1, 0.4*cm))

    # ── 8. SAFETY VALIDATION ──────────────────────────────────────────────────
    story.append(Paragraph("8. Production Safety Validation", S["h1"]))
    safety = result.get("safety", {})
    status = safety.get("status", "UNKNOWN")
    story.append(Paragraph(
        f"<b>Overall Status:</b> <font color='#{_color_hex(safety_color(status))}'>{status}</font> — "
        f"{safety.get('summary', '')}",
        S["body"]
    ))
    story.append(Spacer(1, 0.2*cm))

    checks = safety.get("checks", [])
    if checks:
        check_data = [["Check", "Result", "Note"]]
        for c in checks:
            passed = c.get("passed", True)
            check_data.append([
                c.get("check", ""),
                "PASS" if passed else "FAIL",
                Paragraph(c.get("note", ""), S["body"])
            ])
        tbl4 = Table(check_data, colWidths=[6*cm, 2*cm, 9*cm])
        tbl4.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), C_TEXT),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8.5),
            ("GRID",       (0,0), (-1,-1), 0.4, C_BORDER),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_LIGHT_BG, colors.white]),
            ("LEFTPADDING", (0,0), (-1,-1), 7),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ]))
        story.append(tbl4)

    story.append(Spacer(1, 0.4*cm))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=8))
    story.append(Paragraph(
        "Generated by QueryLens SQL Optimization Platform · For internal DBA review only",
        S["center"]
    ))

    doc.build(story)
    return filepath


def _color_hex(c: colors.Color) -> str:
    """Return hex string (without #) for inline Paragraph color."""
    try:
        r = int(c.red * 255)
        g = int(c.green * 255)
        b = int(c.blue * 255)
        return f"{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "000000"
