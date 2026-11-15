from io import BytesIO
from xml.sax.saxutils import escape
from urllib.parse import urlsplit
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


def _safe(value):
    return escape(str(value or "").replace("\r\n", "\n").replace("\r", "\n")).replace("\n", "<br/>")


def generate_pdf(results, freshness_score=None):
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles, story = getSampleStyleSheet(), [Paragraph("Stale-Answer Detector Report", getSampleStyleSheet()["Title"]), Spacer(1, 20)]
    if freshness_score is not None:
        story += [Paragraph(f"<b>Overall freshness score:</b> {int(freshness_score)}/100", styles["BodyText"]), Spacer(1, 15)]
    for index, item in enumerate(results, start=1):
        story += [Paragraph(f"Claim {index}", styles["Heading2"]), Paragraph(_safe(item.get("claim")), styles["BodyText"]), Spacer(1, 8), Paragraph(f"<b>Status:</b> {_safe(item.get('status', 'Unknown'))}", styles["BodyText"]), Paragraph(f"<b>Explanation:</b> {_safe(item.get('explanation'))}", styles["BodyText"]), Paragraph(f"<b>Freshness:</b> {_safe(item.get('freshness_note'))}", styles["BodyText"]), Spacer(1, 12)]
        for source in item.get("sources", []):
            url = source.get("url", "")
            parsed = urlsplit(url) if isinstance(url, str) else None
            title = _safe(source.get("title", "Source"))
            if parsed and parsed.scheme in {"http", "https"} and parsed.netloc:
                story.append(Paragraph(f'<link href="{escape(url, {chr(34): "&quot;", chr(39): "&apos;"})}" color="blue">{title}</link>', styles["BodyText"]))
            else:
                story.append(Paragraph(title, styles["BodyText"]))
        story.append(Spacer(1, 20))
    document.build(story)
    buffer.seek(0)
    return buffer.getvalue()

