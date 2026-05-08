print("[pdf_service.py] Loading PDF service...")

import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from utils.constants import CHAPTER_NAMES, REFERENCE_HEADINGS


# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
# Nigerian university standard format:
# Times New Roman 12pt, double-spaced, 1.5 inch left margin

LEFT_MARGIN   = 1.5 * inch
RIGHT_MARGIN  = 1.0 * inch
TOP_MARGIN    = 1.0 * inch
BOTTOM_MARGIN = 1.0 * inch

FONT_BODY     = "Times-Roman"
FONT_BOLD     = "Times-Bold"
FONT_ITALIC   = "Times-Italic"
FONT_SIZE     = 12
LINE_SPACING  = 24   # ~double spacing at 12pt


def _build_styles() -> dict:
    """Build all paragraph styles for the project document."""
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "ProjectTitle",
            fontName=FONT_BOLD,
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=20,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName=FONT_BODY,
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=18,
        ),
        "chapter_heading": ParagraphStyle(
            "ChapterHeading",
            fontName=FONT_BOLD,
            fontSize=14,
            alignment=TA_CENTER,
            spaceBefore=24,
            spaceAfter=18,
            leading=20,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            fontName=FONT_BOLD,
            fontSize=12,
            alignment=TA_LEFT,
            spaceBefore=18,
            spaceAfter=6,
            leading=18,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=FONT_BODY,
            fontSize=FONT_SIZE,
            alignment=TA_JUSTIFY,
            leading=LINE_SPACING,
            spaceAfter=12,
            firstLineIndent=36,
        ),
        "body_no_indent": ParagraphStyle(
            "BodyNoIndent",
            fontName=FONT_BODY,
            fontSize=FONT_SIZE,
            alignment=TA_JUSTIFY,
            leading=LINE_SPACING,
            spaceAfter=12,
        ),
        "reference": ParagraphStyle(
            "Reference",
            fontName=FONT_BODY,
            fontSize=11,
            alignment=TA_JUSTIFY,
            leading=18,
            spaceAfter=8,
            leftIndent=36,
            firstLineIndent=-36,   # Hanging indent
        ),
        "disclaimer": ParagraphStyle(
            "Disclaimer",
            fontName=FONT_ITALIC,
            fontSize=10,
            alignment=TA_CENTER,
            leading=14,
            textColor=HexColor("#666666"),
        ),
        "centered": ParagraphStyle(
            "Centered",
            fontName=FONT_BODY,
            fontSize=FONT_SIZE,
            alignment=TA_CENTER,
            leading=LINE_SPACING,
            spaceAfter=6,
        ),
        "bold_centered": ParagraphStyle(
            "BoldCentered",
            fontName=FONT_BOLD,
            fontSize=FONT_SIZE,
            alignment=TA_CENTER,
            leading=LINE_SPACING,
            spaceAfter=6,
        ),
    }
    return styles


# ─── TITLE PAGE ───────────────────────────────────────────────────────────────

def _build_title_page(project: dict, user: dict, styles: dict) -> list:
    """Build the preliminary title page elements."""
    print("[pdf] Building title page...")
    elements = []

    university = project.get("university", "Nigerian University")
    department = project.get("department", "")
    topic      = project.get("topic", "")
    level      = project.get("academic_level", "bsc").upper()
    year       = datetime.now().year

    student_name = user.get("first_name", "Student") if user else "Student"

    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph(university.upper(), styles["title"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(HRFlowable(width="80%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"DEPARTMENT OF {department.upper()}" if department else "DEPARTMENT",
        styles["subtitle"],
    ))
    elements.append(Spacer(1, 0.6 * inch))

    elements.append(Paragraph(topic.upper(), styles["title"]))
    elements.append(Spacer(1, 0.6 * inch))

    elements.append(Paragraph("A Research Project Submitted to the", styles["centered"]))
    elements.append(Paragraph(
        f"Department of {department}",
        styles["centered"],
    ))
    elements.append(Paragraph(
        f"{university}",
        styles["centered"],
    ))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(
        "In Partial Fulfilment of the Requirements for the Award of the Degree of",
        styles["centered"],
    ))
    elements.append(Paragraph(
        _get_degree_name(level),
        styles["bold_centered"],
    ))
    elements.append(Spacer(1, 0.6 * inch))

    elements.append(Paragraph("BY", styles["centered"]))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(student_name.upper(), styles["bold_centered"]))
    elements.append(Spacer(1, 0.6 * inch))

    elements.append(HRFlowable(width="80%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(str(year), styles["centered"]))
    elements.append(PageBreak())

    return elements


def _get_degree_name(level: str) -> str:
    return {
        "BSC":   "Bachelor of Science",
        "BA":    "Bachelor of Arts",
        "HND":   "Higher National Diploma",
        "PGD":   "Postgraduate Diploma",
        "MSC":   "Master of Science",
        "MBA":   "Master of Business Administration",
        "MPA":   "Master of Public Administration",
        "PHD":   "Doctor of Philosophy",
        "NOUN":  "Bachelor's Degree",
    }.get(level.upper(), "Bachelor of Science")


# ─── CERTIFICATION PAGE ───────────────────────────────────────────────────────

def _build_certification_page(project: dict, styles: dict) -> list:
    """Certification/Declaration pages."""
    print("[pdf] Building certification page...")
    elements = []

    elements.append(Paragraph("CERTIFICATION", styles["chapter_heading"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        "This is to certify that this research project was carried out by the above-named student "
        "under my supervision and has been found satisfactory for submission to the Department "
        f"of {project.get('department', '')} in partial fulfilment of the requirements for the "
        f"award of the degree.",
        styles["body"],
    ))
    elements.append(Spacer(1, 0.8 * inch))

    # Signature lines
    sig_data = [
        ["_____________________________", "     ", "_____________________________"],
        ["Supervisor", "     ", "Date"],
        ["", "     ", ""],
        ["_____________________________", "     ", "_____________________________"],
        ["Head of Department", "     ", "Date"],
    ]
    sig_table = Table(sig_data, colWidths=[2.5*inch, 0.5*inch, 2.5*inch])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_BODY),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN",    (0, 0), (-1, -1), "LEFT"),
    ]))
    elements.append(sig_table)
    elements.append(PageBreak())

    # Declaration page
    elements.append(Paragraph("DECLARATION", styles["chapter_heading"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        "I declare that this research project is my original work and has not been submitted "
        "for any other degree or qualification in this or any other university. All sources used "
        "have been duly acknowledged.",
        styles["body"],
    ))
    elements.append(Spacer(1, 0.8 * inch))

    dec_data = [
        ["_____________________________", "     ", "_____________________________"],
        ["Student's Signature", "     ", "Date"],
    ]
    dec_table = Table(dec_data, colWidths=[2.5*inch, 0.5*inch, 2.5*inch])
    dec_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_BODY),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN",    (0, 0), (-1, -1), "LEFT"),
    ]))
    elements.append(dec_table)
    elements.append(PageBreak())

    return elements


# ─── ABSTRACT PAGE ────────────────────────────────────────────────────────────

def _build_abstract_page(project: dict, styles: dict) -> list:
    """Build abstract page — placeholder if not yet generated."""
    print("[pdf] Building abstract page...")
    elements = []
    elements.append(Paragraph("ABSTRACT", styles["chapter_heading"]))
    elements.append(Spacer(1, 0.2 * inch))

    ch1 = project.get("chapter_1_content", "")
    if ch1:
        # Extract first 300 words as abstract approximation
        words   = ch1.split()[:300]
        preview = " ".join(words) + "..."
        elements.append(Paragraph(preview, styles["body"]))
    else:
        elements.append(Paragraph(
            "[Abstract will appear here after Chapter 1 is generated]",
            styles["body"],
        ))

    elements.append(Spacer(1, 0.3 * inch))

    # Keywords
    topic_words = project.get("topic", "").split()[:6]
    keywords    = ", ".join(topic_words)
    elements.append(Paragraph(
        f"<b>Keywords:</b> {keywords}",
        styles["body_no_indent"],
    ))
    elements.append(PageBreak())
    return elements


# ─── TABLE OF CONTENTS ────────────────────────────────────────────────────────

def _build_table_of_contents(project: dict, styles: dict) -> list:
    """Build a basic table of contents."""
    print("[pdf] Building table of contents...")
    elements = []
    elements.append(Paragraph("TABLE OF CONTENTS", styles["chapter_heading"]))
    elements.append(Spacer(1, 0.2 * inch))

    toc_items = [
        ("Title Page",       "i"),
        ("Certification",    "ii"),
        ("Declaration",      "iii"),
        ("Abstract",         "iv"),
        ("Table of Contents","v"),
        ("", ""),
    ]

    chapters_done = project.get("chapters_completed", 0)
    for ch_num in range(1, 6):
        ch_name = CHAPTER_NAMES.get(ch_num, f"Chapter {ch_num}")
        page_placeholder = str(ch_num) if ch_num <= chapters_done else "-"
        toc_items.append((
            f"Chapter {ch_num}: {ch_name}",
            page_placeholder,
        ))

    toc_items += [
        ("", ""),
        ("References", "-"),
        ("Appendix",   "-"),
    ]

    for label, page in toc_items:
        if not label:
            elements.append(Spacer(1, 6))
            continue
        toc_data = [[label, page]]
        toc_table = Table(
            toc_data,
            colWidths=[5.0 * inch, 0.8 * inch],
        )
        toc_table.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (-1, -1), FONT_BODY),
            ("FONTSIZE",  (0, 0), (-1, -1), 11),
            ("ALIGN",     (1, 0), (1, 0),   "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(toc_table)

    elements.append(PageBreak())
    return elements


# ─── CHAPTER CONTENT ──────────────────────────────────────────────────────────

def _build_chapter(
    chapter_number: int,
    content: str,
    styles: dict,
) -> list:
    """Convert a chapter's text content into PDF elements."""
    import re
    print(f"[pdf] Building chapter {chapter_number}...")
    elements = []

    chapter_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")
    elements.append(Paragraph(
        f"CHAPTER {chapter_number}",
        styles["chapter_heading"],
    ))
    elements.append(Paragraph(
        chapter_name.upper(),
        styles["chapter_heading"],
    ))
    elements.append(Spacer(1, 0.2 * inch))

    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            elements.append(Spacer(1, 6))
            continue

        if _is_section_heading(line):
            # Strip markdown # markers for display
            clean_heading = re.sub(r'^#{1,6}\s+', '', line).strip()
            elements.append(Paragraph(clean_heading, styles["section_heading"]))
        elif line.startswith("|") and "|" in line[1:]:
            elements.append(Paragraph(line, styles["body_no_indent"]))
        else:
            clean = _clean_markdown(line)
            if clean:
                elements.append(Paragraph(clean, styles["body"]))

    elements.append(PageBreak())
    return elements


def _is_section_heading(line: str) -> bool:
    """Detect section headings — numbered (1.1) or markdown (#)."""
    import re
    if re.match(r'^#{1,6}\s+', line.strip()):
        return True
    if re.match(r'^\d+\.\d+(\.\d+)?\s+\w', line.strip()):
        return True
    return False

def _clean_markdown(text: str) -> str:
    """Convert markdown to ReportLab XML and strip heading markers."""
    import re

    # Strip markdown heading markers ## ### #
    text = re.sub(r'^#{1,6}\s+', '', text.strip())

    # Strip horizontal rules
    text = re.sub(r'^[-*_]{3,}$', '', text)

    # Bold: **text** → <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Italic: *text* or _text_ → <i>text</i>
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_',   r'<i>\1</i>', text)

    # Protect our tags before escaping
    text = text.replace('<b>', 'BOPEN').replace('</b>', 'BCLOSE')
    text = text.replace('<i>', 'IOPEN').replace('</i>', 'ICLOSE')

    # Escape XML special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')

    # Restore our tags
    text = text.replace('BOPEN', '<b>').replace('BCLOSE', '</b>')
    text = text.replace('IOPEN', '<i>').replace('ICLOSE', '</i>')

    return text.strip()

# ─── REFERENCE LIST ───────────────────────────────────────────────────────────

def _build_reference_list(project: dict, styles: dict) -> list:
    """Build the reference list from verified citations stored in Supabase."""
    print("[pdf] Building reference list...")
    elements = []

    citation_style = project.get("citation_style", "apa7")
    heading = REFERENCE_HEADINGS.get(citation_style, "References")

    elements.append(Paragraph(heading.upper(), styles["chapter_heading"]))
    elements.append(Spacer(1, 0.2 * inch))

    refs_raw = project.get("verified_references", [])
    if isinstance(refs_raw, str):
        try:
            refs_raw = json.loads(refs_raw)
        except Exception:
            refs_raw = []

    if not refs_raw:
        elements.append(Paragraph(
            "[References will appear here after Chapter 2 is generated]",
            styles["body"],
        ))
        elements.append(PageBreak())
        return elements

    # Sort alphabetically by first author surname for APA/Harvard/Chicago/MLA
    ieee_styles = {"ieee", "vancouver"}
    if citation_style not in ieee_styles:
        refs_raw = sorted(
            refs_raw,
            key=lambda r: (r.get("authors", [""])[0].split()[-1]
                           if r.get("authors") else ""),
        )

    for i, ref in enumerate(refs_raw, 1):
        formatted = _format_single_reference(ref, citation_style, i)
        elements.append(Paragraph(formatted, styles["reference"]))

    elements.append(PageBreak())
    return elements


def _format_single_reference(ref: dict, style: str, number: int) -> str:
    """Format a single reference in the specified citation style."""
    authors  = ref.get("authors", [])
    year     = ref.get("year", "n.d.")
    title    = ref.get("title", "Unknown Title")
    journal  = ref.get("journal", "")
    doi      = ref.get("doi", "")
    doi_url  = f"https://doi.org/{doi}" if doi else ""

    # Format author list
    def _apa_authors(authors: list) -> str:
        if not authors:
            return "Unknown Author"
        formatted = []
        for name in authors[:6]:
            parts = name.strip().split()
            if len(parts) >= 2:
                surname  = parts[-1]
                initials = ". ".join(p[0] for p in parts[:-1]) + "."
                formatted.append(f"{surname}, {initials}")
            else:
                formatted.append(name)
        if len(authors) > 6:
            formatted.append("et al.")
        if len(formatted) > 1:
            return ", ".join(formatted[:-1]) + ", &amp; " + formatted[-1]
        return formatted[0] if formatted else "Unknown"

    def _ieee_authors(authors: list) -> str:
        if not authors:
            return "Unknown"
        formatted = []
        for name in authors[:6]:
            parts = name.strip().split()
            if len(parts) >= 2:
                initials = ". ".join(p[0] for p in parts[:-1]) + "."
                surname  = parts[-1]
                formatted.append(f"{initials} {surname}")
            else:
                formatted.append(name)
        if len(authors) > 6:
            formatted.append("et al.")
        return ", ".join(formatted)

    doi_text = f" {doi_url}" if doi_url else ""

    if style == "apa7":
        author_str = _apa_authors(authors)
        journal_str = f"<i>{journal}</i>. " if journal else ""
        return f"{author_str} ({year}). {title}. {journal_str}{doi_text}"

    elif style == "harvard":
        author_str = _apa_authors(authors)
        journal_str = f"<i>{journal}</i>. " if journal else ""
        return f"{author_str} ({year}) '{title}', {journal_str}{doi_text}"

    elif style == "ieee":
        author_str = _ieee_authors(authors)
        journal_str = f"<i>{journal}</i>, " if journal else ""
        return f"[{number}] {author_str}, '{title},' {journal_str}{year}.{doi_text}"

    elif style == "vancouver":
        author_str = _ieee_authors(authors)
        journal_str = f"{journal}. " if journal else ""
        return f"{number}. {author_str}. {title}. {journal_str}{year}.{doi_text}"

    elif style in ("chicago", "mla"):
        author_str = _apa_authors(authors)
        journal_str = f"<i>{journal}</i>. " if journal else ""
        return f"{author_str}. &quot;{title}.&quot; {journal_str}({year}).{doi_text}"

    # Default to APA
    author_str = _apa_authors(authors)
    return f"{author_str} ({year}). {title}.{doi_text}"


# ─── APPENDIX ─────────────────────────────────────────────────────────────────

def _build_appendix(styles: dict) -> list:
    """Appendix placeholder."""
    elements = []
    elements.append(Paragraph("APPENDIX", styles["chapter_heading"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Appendix A: Research Questionnaire", styles["section_heading"]))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(
        "[Insert printed questionnaire here]",
        styles["body"],
    ))
    elements.append(PageBreak())
    return elements


# ─── DISCLAIMER PAGE ──────────────────────────────────────────────────────────

def _build_disclaimer_page(styles: dict) -> list:
    elements = []
    elements.append(PageBreak())
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph(
        "AI ASSISTANCE DISCLOSURE",
        styles["bold_centered"],
    ))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        "This project was prepared with the assistance of FYP Mentor, an AI research assistant. "
        "The student is responsible for reviewing, verifying, editing, and taking full ownership "
        "of all content before submission. All citations have been verified against published "
        "academic sources. The student must confirm all facts, figures, and references with "
        "their supervisor prior to submission.",
        styles["disclaimer"],
    ))
    return elements


# ─── PAGE NUMBER FOOTER ───────────────────────────────────────────────────────

def _add_page_numbers(canvas, doc):
    """Add page numbers to every page."""
    canvas.saveState()
    canvas.setFont(FONT_BODY, 10)
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(
        A4[0] / 2,
        0.5 * inch,
        str(page_num),
    )
    canvas.restoreState()


# ─── MAIN PDF GENERATION FUNCTION ─────────────────────────────────────────────

def generate_project_pdf(project: dict, user: dict = None) -> io.BytesIO:
    """
    Generate the complete project PDF in memory.
    Returns a BytesIO buffer ready to send as a Telegram document.
    Never writes to disk.
    """
    print(f"[pdf] generate_project_pdf: project_id={project.get('id')}")

    buffer = io.BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title=project.get("topic", "Research Project"),
        author=user.get("first_name", "Student") if user else "Student",
    )

    elements = []

    # ── Preliminary pages ──────────────────────────────────────────────────────
    elements += _build_title_page(project, user or {}, styles)
    elements += _build_certification_page(project, styles)
    elements += _build_abstract_page(project, styles)
    elements += _build_table_of_contents(project, styles)

    # ── Chapters ───────────────────────────────────────────────────────────────
    chapters_done = project.get("chapters_completed", 0)
    for ch_num in range(1, chapters_done + 1):
        content = project.get(f"chapter_{ch_num}_content", "")
        if content:
            elements += _build_chapter(ch_num, content, styles)
            print(f"[pdf] Chapter {ch_num} added to PDF")

    # ── Reference list ─────────────────────────────────────────────────────────
    elements += _build_reference_list(project, styles)

    # ── Appendix ───────────────────────────────────────────────────────────────
    elements += _build_appendix(styles)

    # ── Disclaimer ─────────────────────────────────────────────────────────────
    elements += _build_disclaimer_page(styles)

    # ── Build PDF ──────────────────────────────────────────────────────────────
    doc.build(
        elements,
        onFirstPage=_add_page_numbers,
        onLaterPages=_add_page_numbers,
    )

    buffer.seek(0)
    size_kb = len(buffer.getvalue()) // 1024
    print(f"[pdf] PDF generated successfully. Size: {size_kb} KB")
    return buffer


print("[pdf_service.py] PDF service loaded.")