print("[pdf_service.py] Loading PDF service...")

import io
import json
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
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
# Nigerian university standard: Times New Roman 12pt, double-spaced
# Margins: 1.5 inch left, 1 inch right/top/bottom

LEFT_MARGIN   = 1.5 * inch
RIGHT_MARGIN  = 1.0 * inch
TOP_MARGIN    = 1.0 * inch
BOTTOM_MARGIN = 1.0 * inch

FONT_BODY     = "Times-Roman"
FONT_BOLD     = "Times-Bold"
FONT_ITALIC   = "Times-Italic"
FONT_BOLD_ITALIC = "Times-BoldItalic"
FONT_SIZE     = 12
LINE_SPACING  = 24   # double spacing at 12pt


def _styles() -> dict:
    """Build all paragraph styles matching the benchmark project format."""
    return {
        # Title page — centered, bold, all caps
        "cover_title": ParagraphStyle(
            "CoverTitle",
            fontName=FONT_BOLD,
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=12,
            leading=22,
        ),
        "cover_normal": ParagraphStyle(
            "CoverNormal",
            fontName=FONT_BODY,
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=20,
        ),
        "cover_bold": ParagraphStyle(
            "CoverBold",
            fontName=FONT_BOLD,
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=20,
        ),
        # Chapter heading — bold, centered, ALL CAPS
        "chapter_heading": ParagraphStyle(
            "ChapterHeading",
            fontName=FONT_BOLD,
            fontSize=12,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=24,
            leading=20,
        ),
        # Section heading — bold, left, numbered
        "section_heading": ParagraphStyle(
            "SectionHeading",
            fontName=FONT_BOLD,
            fontSize=12,
            alignment=TA_LEFT,
            spaceBefore=18,
            spaceAfter=6,
            leading=20,
        ),
        # Body text — Times Roman 12pt, double spaced, justified, first line indent
        "body": ParagraphStyle(
            "Body",
            fontName=FONT_BODY,
            fontSize=FONT_SIZE,
            alignment=TA_JUSTIFY,
            leading=LINE_SPACING,
            spaceAfter=0,
            firstLineIndent=36,
        ),
        # Body without indent (after headings)
        "body_no_indent": ParagraphStyle(
            "BodyNoIndent",
            fontName=FONT_BODY,
            fontSize=FONT_SIZE,
            alignment=TA_JUSTIFY,
            leading=LINE_SPACING,
            spaceAfter=0,
        ),
        # Reference entries — hanging indent
        "reference": ParagraphStyle(
            "Reference",
            fontName=FONT_BODY,
            fontSize=11,
            alignment=TA_JUSTIFY,
            leading=20,
            spaceAfter=10,
            leftIndent=36,
            firstLineIndent=-36,
        ),
        # Figure caption — bold, centered
        "figure_caption": ParagraphStyle(
            "FigureCaption",
            fontName=FONT_BOLD,
            fontSize=12,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=12,
            leading=18,
        ),
        # Disclaimer
        "disclaimer": ParagraphStyle(
            "Disclaimer",
            fontName=FONT_ITALIC,
            fontSize=10,
            alignment=TA_CENTER,
            leading=14,
            textColor=HexColor("#555555"),
        ),
        # Preliminary page headings (DECLARATION, CERTIFICATION etc.)
        "prelim_heading": ParagraphStyle(
            "PrelimHeading",
            fontName=FONT_BOLD,
            fontSize=12,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=24,
            leading=20,
        ),
        # Table of contents entry
        "toc_entry": ParagraphStyle(
            "TOCEntry",
            fontName=FONT_BODY,
            fontSize=12,
            alignment=TA_LEFT,
            leading=24,
            spaceAfter=0,
        ),
        "toc_chapter": ParagraphStyle(
            "TOCChapter",
            fontName=FONT_BOLD,
            fontSize=12,
            alignment=TA_LEFT,
            leading=24,
            spaceAfter=0,
        ),
    }


# ─── PAGE NUMBER CALLBACK ─────────────────────────────────────────────────────

class _PageNumCanvas:
    """Tracks page number state for the document."""
    pass


def _add_page_numbers(canvas, doc):
    """Add centered page numbers at bottom of every page."""
    canvas.saveState()
    canvas.setFont(FONT_BODY, 12)
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(A4[0] / 2, 0.5 * inch, str(page_num))
    canvas.restoreState()


def _no_page_numbers(canvas, doc):
    """No page numbers on preliminary pages."""
    pass


# ─── TITLE PAGES ──────────────────────────────────────────────────────────────

def _build_title_pages(project: dict, user: dict, s: dict) -> list:
    """
    Build two title pages matching the benchmark format:
    Page 1: Cover page (title, author, matric, dept, school, university, date)
    Page 2: Submission page (title, by, name, matric, submission statement, date)
    """
    print("[pdf] Building title pages...")
    elements = []

    university   = project.get("university", "Nigerian University")
    department   = project.get("department", "")
    topic        = project.get("topic", "").upper()
    level        = (project.get("academic_level") or "bsc").upper()
    year         = str(datetime.now().year)
    student_name = (user.get("first_name", "Student") if user else "Student").upper()

    degree_name = {
        "BSC":   "Bachelor of Science",
        "HND":   "Higher National Diploma",
        "PGD":   "Postgraduate Diploma",
        "MSC":   "Master of Science",
        "MBA":   "Master of Business Administration",
        "MPA":   "Master of Public Administration",
        "PHD":   "Doctor of Philosophy",
        "NOUN":  "Bachelor's Degree",
    }.get(level, "Bachelor of Science")

    # ── Cover Page ────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.8 * inch))
    elements.append(Paragraph(topic, s["cover_title"]))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("BY", s["cover_bold"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(student_name, s["cover_bold"]))
    elements.append(Spacer(1, 1.5 * inch))

    if department:
        elements.append(Paragraph(f"DEPARTMENT OF {department.upper()}", s["cover_normal"]))
    elements.append(Paragraph(university.upper(), s["cover_normal"]))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph(f"{_month_year(year)}.", s["cover_normal"]))
    elements.append(PageBreak())

    # ── Submission Page ───────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.8 * inch))
    elements.append(Paragraph(topic, s["cover_title"]))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("BY", s["cover_bold"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(student_name, s["cover_bold"]))
    elements.append(Spacer(1, 0.5 * inch))

    elements.append(Paragraph(
        f"A PROJECT REPORT SUBMITTED TO THE DEPARTMENT OF "
        f"{department.upper() if department else 'THE DEPARTMENT'}, "
        f"{university.upper()}, IN PARTIAL FULFILLMENT FOR THE AWARD OF "
        f"{degree_name.upper()} DEGREE.",
        s["cover_normal"],
    ))
    elements.append(Spacer(1, 0.8 * inch))
    elements.append(Paragraph(f"{_month_year(year)}.", s["cover_normal"]))
    elements.append(PageBreak())

    return elements


def _month_year(year: str) -> str:
    months = [
        "", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
    ]
    month = months[datetime.now().month]
    return f"{month}, {year}"


# ─── PRELIMINARY PAGES ────────────────────────────────────────────────────────

def _build_declaration(project: dict, user: dict, s: dict) -> list:
    print("[pdf] Building declaration page...")
    elements = []
    topic        = project.get("topic", "")
    student_name = (user.get("first_name", "Student") if user else "Student").upper()

    elements.append(Paragraph("DECLARATION", s["prelim_heading"]))
    elements.append(Paragraph(
        f'I hereby declare that the study titled: "{topic}" is a collection of my '
        f"original research work, and it has not been presented for any other qualification anywhere. "
        f"Information from other sources (published and unpublished) has been duly acknowledged.",
        s["body_no_indent"],
    ))
    elements.append(Spacer(1, 0.8 * inch))

    sig_data = [
        ["...............................................", "......................................"],
        [student_name, "Date"],
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 2.5 * inch])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_BODY),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("ALIGN",    (0, 0), (-1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(sig_table)
    elements.append(PageBreak())
    return elements


def _build_certification(project: dict, user: dict, s: dict) -> list:
    print("[pdf] Building certification page...")
    elements = []
    topic      = project.get("topic", "")
    student_name = (user.get("first_name", "Student") if user else "Student").upper()
    university = project.get("university", "the University")
    department = project.get("department", "the Department")
    level      = (project.get("academic_level") or "bsc").upper()
    degree     = {"BSC": "Bachelor of Science", "MSC": "Master of Science",
                  "MBA": "MBA", "PHD": "Doctor of Philosophy"}.get(level, "Bachelor of Science")

    elements.append(Paragraph("CERTIFICATION", s["prelim_heading"]))
    elements.append(Paragraph(
        f'This project report, entitled "{topic}" by {student_name}, '
        f"meets the regulations governing the award of the degree of {degree} "
        f"in {department} of {university}, and is approved for its contribution "
        f"to knowledge and literary presentation.",
        s["body_no_indent"],
    ))
    elements.append(Spacer(1, 0.6 * inch))

    rows = [
        ["...............................................", "......................................"],
        ["Project Supervisor", "Date"],
        ["", ""],
        ["...............................................", "......................................"],
        ["Head of Department", "Date"],
        ["", ""],
        ["...............................................", "......................................"],
        ["External Examiner", "Date"],
    ]
    t = Table(rows, colWidths=[3.5 * inch, 2.5 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_BODY),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("ALIGN",    (0, 0), (-1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t)
    elements.append(PageBreak())
    return elements


def _build_dedication(s: dict) -> list:
    print("[pdf] Building dedication page...")
    elements = []
    elements.append(Paragraph("DEDICATION", s["prelim_heading"]))
    elements.append(Paragraph(
        "This project is dedicated to my family, whose unwavering support and encouragement "
        "made this work possible.",
        s["body_no_indent"],
    ))
    elements.append(PageBreak())
    return elements


def _build_acknowledgement(user: dict, s: dict) -> list:
    print("[pdf] Building acknowledgement page...")
    elements = []
    elements.append(Paragraph("ACKNOWLEDGEMENT", s["prelim_heading"]))
    elements.append(Paragraph(
        "I extend my heartfelt gratitude to God Almighty, whose guidance has seen me through "
        "the successful completion of this project. I also thank my supervisor, my head of "
        "department, and all the lecturers who contributed to my academic journey. Special "
        "appreciation goes to my family and friends for their continuous support and encouragement.",
        s["body_no_indent"],
    ))
    elements.append(PageBreak())
    return elements


def _build_abstract(project: dict, s: dict) -> list:
    print("[pdf] Building abstract page...")
    elements = []
    elements.append(Paragraph("ABSTRACT", s["prelim_heading"]))

    ch1 = project.get("chapter_1_content", "")
    if ch1:
        words = ch1.split()[:300]
        abstract_text = " ".join(words)
        if len(ch1.split()) > 300:
            abstract_text += "..."
        elements.append(Paragraph(abstract_text, s["body_no_indent"]))
    else:
        elements.append(Paragraph(
            "[Abstract will appear here after Chapter 1 is generated and reviewed.]",
            s["body_no_indent"],
        ))

    elements.append(Spacer(1, 0.3 * inch))
    topic_words = project.get("topic", "").split()[:6]
    keywords = ", ".join(topic_words)
    elements.append(Paragraph(
        f"<b>Keywords:</b> {keywords}",
        s["body_no_indent"],
    ))
    elements.append(PageBreak())
    return elements


def _build_toc(project: dict, s: dict) -> list:
    print("[pdf] Building table of contents...")
    elements = []
    elements.append(Paragraph("TABLE OF CONTENTS", s["prelim_heading"]))

    prelim_pages = [
        ("Title page", "i"),
        ("Declaration", "iii"),
        ("Certification", "iv"),
        ("Dedication", "v"),
        ("Acknowledgement", "vi"),
        ("Abstract", "vii"),
        ("Table of Contents", "viii"),
        ("List of Figures", "xi"),
    ]

    for label, page in prelim_pages:
        row_data = [[label, page]]
        t = Table(row_data, colWidths=[5.2 * inch, 0.8 * inch])
        t.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, -1), FONT_BODY),
            ("FONTSIZE",      (0, 0), (-1, -1), 12),
            ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ]))
        elements.append(t)

    elements.append(Spacer(1, 12))
    chapters_done = project.get("chapters_completed", 0)
    for ch_num in range(1, 6):
        ch_name = CHAPTER_NAMES.get(ch_num, f"Chapter {ch_num}")
        page_ref = str(ch_num) if ch_num <= chapters_done else "-"
        label = f"CHAPTER {ch_num}"

        row_data = [[label, page_ref]]
        t = Table(row_data, colWidths=[5.2 * inch, 0.8 * inch])
        t.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, -1), FONT_BOLD),
            ("FONTSIZE",      (0, 0), (-1, -1), 12),
            ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)

        sub_label = ch_name
        sub_data = [[sub_label, ""]]
        t2 = Table(sub_data, colWidths=[5.2 * inch, 0.8 * inch])
        t2.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, -1), FONT_BODY),
            ("FONTSIZE",      (0, 0), (-1, -1), 12),
            ("LEFTPADDING",   (0, 0), (0, 0),   24),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ]))
        elements.append(t2)

    elements.append(Spacer(1, 12))
    for label in ["REFERENCES", "APPENDIX"]:
        row_data = [[label, "-"]]
        t = Table(row_data, colWidths=[5.2 * inch, 0.8 * inch])
        t.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, -1), FONT_BOLD),
            ("FONTSIZE",      (0, 0), (-1, -1), 12),
            ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)

    elements.append(PageBreak())
    return elements


# ─── CHAPTER CONTENT ──────────────────────────────────────────────────────────

def _build_chapter(chapter_number: int, content: str, s: dict) -> list:
    """Convert chapter text to properly formatted PDF elements."""
    print(f"[pdf] Building chapter {chapter_number}...")
    elements = []

    chapter_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")

    # Chapter heading — CHAPTER ONE\n\nINTRODUCTION style
    elements.append(Paragraph(
        f"CHAPTER {_number_to_word(chapter_number)}",
        s["chapter_heading"],
    ))
    elements.append(Paragraph(
        f"{chapter_number}.0 {chapter_name.upper()}",
        s["chapter_heading"],
    ))

    lines = content.split("\n")
    first_para = True

    for line in lines:
        line = line.strip()
        if not line:
            elements.append(Spacer(1, LINE_SPACING))
            first_para = False
            continue

        # Detect section headings
        if _is_section_heading(line):
            clean = re.sub(r'^#{1,6}\s*', '', line).strip()
            elements.append(Paragraph(clean, s["section_heading"]))
            first_para = True
            continue

        # Skip markdown table rows
        if line.startswith("|") and "|" in line[1:]:
            elements.append(Paragraph(_clean_line(line), s["body_no_indent"]))
            continue

        # Body text
        clean = _clean_line(line)
        if clean:
            style = s["body_no_indent"] if first_para else s["body"]
            elements.append(Paragraph(clean, style))
            first_para = False

    elements.append(PageBreak())
    return elements


def _number_to_word(n: int) -> str:
    words = {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE"}
    return words.get(n, str(n))


def _is_section_heading(line: str) -> bool:
    import re
    if re.match(r'^#{1,6}\s+', line.strip()):
        return True
    if re.match(r'^\d+\.\d+(\.\d+)?\s+\S', line.strip()):
        return True
    return False


def _clean_line(text: str) -> str:
    """Strip markdown, escape XML for ReportLab."""
    import re
    # Strip heading markers
    text = re.sub(r'^#{1,6}\s+', '', text.strip())
    # Bold: **text** → <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Italic: *text* or _text_ → <i>text</i>
    text = re.sub(r'\*(.+?)\*',   r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_',     r'<i>\1</i>', text)

    # Protect tags
    text = text.replace('<b>', 'BOPEN').replace('</b>', 'BCLOSE')
    text = text.replace('<i>', 'IOPEN').replace('</i>', 'ICLOSE')

    # Escape XML chars
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')

    # Restore tags
    text = text.replace('BOPEN', '<b>').replace('BCLOSE', '</b>')
    text = text.replace('IOPEN', '<i>').replace('ICLOSE', '</i>')

    return text.strip()


# ─── REFERENCE LIST ───────────────────────────────────────────────────────────

def _build_references(project: dict, s: dict) -> list:
    print("[pdf] Building reference list...")
    elements = []

    citation_style = project.get("citation_style", "apa7")
    heading = REFERENCE_HEADINGS.get(citation_style, "References")

    elements.append(Paragraph(heading.upper(), s["chapter_heading"]))

    refs_raw = project.get("verified_references", [])
    if isinstance(refs_raw, str):
        try:
            refs_raw = json.loads(refs_raw)
        except Exception:
            refs_raw = []

    if not refs_raw:
        elements.append(Paragraph(
            "[References will appear here after Chapter 2 is generated]",
            s["body_no_indent"],
        ))
        elements.append(PageBreak())
        return elements

    # Sort alphabetically for author-date styles
    if citation_style not in ("ieee", "vancouver"):
        refs_raw = sorted(
            refs_raw,
            key=lambda r: (
                r.get("authors", [""])[0].split()[-1].lower()
                if r.get("authors") else "zzz"
            ),
        )

    for i, ref in enumerate(refs_raw, 1):
        formatted = _format_reference(ref, citation_style, i)
        if formatted:
            elements.append(Paragraph(formatted, s["reference"]))

    elements.append(PageBreak())
    return elements


def _format_reference(ref: dict, style: str, number: int) -> str:
    authors  = ref.get("authors", [])
    year     = ref.get("year", "n.d.")
    title    = ref.get("title", "Unknown Title")
    journal  = ref.get("journal", "")
    doi      = ref.get("doi", "")
    doi_url  = f"https://doi.org/{doi}" if doi else ""

    def apa_authors(authors):
        if not authors: return "Unknown Author"
        formatted = []
        for name in authors[:6]:
            parts = name.strip().split()
            if len(parts) >= 2:
                surname  = parts[-1]
                initials = ". ".join(p[0].upper() for p in parts[:-1]) + "."
                formatted.append(f"{surname}, {initials}")
            else:
                formatted.append(name)
        if len(authors) > 6: formatted.append("et al.")
        if len(formatted) > 1:
            return ", ".join(formatted[:-1]) + ", &amp; " + formatted[-1]
        return formatted[0]

    def ieee_authors(authors):
        if not authors: return "Unknown"
        formatted = []
        for name in authors[:6]:
            parts = name.strip().split()
            if len(parts) >= 2:
                initials = ". ".join(p[0].upper() for p in parts[:-1]) + "."
                surname  = parts[-1]
                formatted.append(f"{initials} {surname}")
            else:
                formatted.append(name)
        if len(authors) > 6: formatted.append("et al.")
        return ", ".join(formatted)

    j = f"<i>{journal}</i>. " if journal else ""
    d = f" {doi_url}" if doi_url else ""

    if style == "apa7":
        return f"{apa_authors(authors)} ({year}). {title}. {j}{d}".strip()
    elif style == "harvard":
        return f"{apa_authors(authors)} ({year}) '{title}', {j}{d}".strip()
    elif style == "ieee":
        return f"[{number}] {ieee_authors(authors)}, '{title},' {j}{year}.{d}".strip()
    elif style == "vancouver":
        return f"{number}. {ieee_authors(authors)}. {title}. {j}{year}.{d}".strip()
    else:
        return f"{apa_authors(authors)} ({year}). {title}. {j}{d}".strip()


# ─── DISCLAIMER ───────────────────────────────────────────────────────────────

def _build_disclaimer(s: dict) -> list:
    elements = []
    elements.append(PageBreak())
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph("AI ASSISTANCE DISCLOSURE", s["prelim_heading"]))
    elements.append(Paragraph(
        "This project was prepared with the assistance of FYP Mentor, an AI research assistant. "
        "The student is responsible for reviewing, verifying, editing, and taking full ownership "
        "of all content before submission. All citations have been verified against published "
        "academic sources. The student must confirm all facts, figures, and references with "
        "their supervisor prior to submission.",
        s["disclaimer"],
    ))
    return elements


# ─── MAIN PDF GENERATION ──────────────────────────────────────────────────────

def generate_project_pdf(project: dict, user: dict = None) -> io.BytesIO:
    """
    Generate the complete project PDF in memory.
    Matches the format of the accepted FUT Minna benchmark project:
    - Times New Roman 12pt
    - Double spaced
    - 1.5 inch left margin
    - Proper preliminary pages
    - Chapter headings: bold centered ALL CAPS
    - Section headings: bold left numbered
    - References with hanging indent
    Never writes to disk — returns BytesIO buffer.
    """
    print(f"[pdf] generate_project_pdf: project_id={project.get('id')}")

    # Merge user fields
    if user:
        project = dict(project)
        project["university"]     = project.get("university")     or user.get("university", "")
        project["department"]     = project.get("department")     or user.get("department", "")
        project["academic_level"] = project.get("academic_level") or user.get("academic_level", "bsc")
        project["faculty"]        = project.get("faculty")        or user.get("faculty", "")

    buffer = io.BytesIO()
    s = _styles()

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

    # ── Preliminary pages (no page numbers) ───────────────────────────────────
    elements += _build_title_pages(project, user or {}, s)
    elements += _build_declaration(project, user or {}, s)
    elements += _build_certification(project, user or {}, s)
    elements += _build_dedication(s)
    elements += _build_acknowledgement(user or {}, s)
    elements += _build_abstract(project, s)
    elements += _build_toc(project, s)

    # ── Chapters ───────────────────────────────────────────────────────────────
    chapters_done = project.get("chapters_completed", 0)
    for ch_num in range(1, chapters_done + 1):
        content = project.get(f"chapter_{ch_num}_content", "")
        if content:
            elements += _build_chapter(ch_num, content, s)
            print(f"[pdf] Chapter {ch_num} added.")

    # ── References ─────────────────────────────────────────────────────────────
    elements += _build_references(project, s)

    # ── Disclaimer ─────────────────────────────────────────────────────────────
    elements += _build_disclaimer(s)

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(
        elements,
        onFirstPage=_no_page_numbers,
        onLaterPages=_add_page_numbers,
    )

    buffer.seek(0)
    size_kb = len(buffer.getvalue()) // 1024
    print(f"[pdf] PDF generated. Size: {size_kb} KB")
    return buffer


print("[pdf_service.py] PDF service loaded.")