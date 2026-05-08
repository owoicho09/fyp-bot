print("[citation_service.py] Loading citation service...")

import json
from services.search_service import find_citations, find_citations_batch
from services.supabase_service import (
    add_verified_reference, get_verified_references,
)
from utils.constants import CITATION_STYLES


# ─── FORMAT SINGLE CITATION IN-TEXT ──────────────────────────────────────────

def format_intext_citation(paper: dict, style: str) -> str:
    """
    Format a single paper as an in-text citation string.
    Used by Claude when it needs to insert a citation inline.

    Returns e.g.:
        APA7:      (Adeyemi et al., 2024)
        Harvard:   (Adeyemi et al., 2024)
        IEEE:      [1]
        Vancouver: (1)
    """
    authors = paper.get("authors", [])
    year    = paper.get("year", "n.d.")

    if not authors:
        first_author = "Unknown"
    else:
        # Get first author's surname
        name_parts   = authors[0].strip().split()
        first_author = name_parts[-1] if name_parts else "Unknown"

    et_al = " et al." if len(authors) > 2 else (
        f" & {authors[1].strip().split()[-1]}" if len(authors) == 2 else ""
    )

    if style in ("apa7", "harvard"):
        return f"({first_author}{et_al}, {year})"
    elif style == "ieee":
        return "[N]"   # Numbered — Claude handles actual numbering
    elif style == "vancouver":
        return "(N)"   # Numbered — Claude handles actual numbering
    elif style == "oscola":
        return ""      # OSCOLA uses footnotes — Claude handles
    elif style in ("chicago", "mla"):
        return f"({first_author}{et_al}, {year})"
    else:
        return f"({first_author}{et_al}, {year})"


def format_full_reference(paper: dict, style: str, number: int = 1) -> str:
    """
    Format a single paper as a full reference list entry.
    This is used to build the References section injected into Chapter 2 prompt.
    """
    authors  = paper.get("authors", [])
    year     = paper.get("year", "n.d.")
    title    = paper.get("title", "Unknown Title")
    journal  = paper.get("journal", "")
    doi      = paper.get("doi", "")
    doi_url  = f"https://doi.org/{doi}" if doi else ""

    def _surnames_initials(authors: list) -> str:
        """APA/Harvard style: Surname, F. M."""
        if not authors:
            return "Unknown Author"
        formatted = []
        for name in authors[:6]:
            parts = name.strip().split()
            if len(parts) >= 2:
                surname  = parts[-1]
                initials = ". ".join(p[0].upper() for p in parts[:-1]) + "."
                formatted.append(f"{surname}, {initials}")
            else:
                formatted.append(name)
        if len(authors) > 6:
            formatted.append("et al.")
        if len(formatted) > 1:
            return ", ".join(formatted[:-1]) + ", & " + formatted[-1]
        return formatted[0]

    def _initials_surname(authors: list) -> str:
        """IEEE/Vancouver style: F. M. Surname"""
        if not authors:
            return "Unknown"
        formatted = []
        for name in authors[:6]:
            parts = name.strip().split()
            if len(parts) >= 2:
                initials = ". ".join(p[0].upper() for p in parts[:-1]) + "."
                surname  = parts[-1]
                formatted.append(f"{initials} {surname}")
            else:
                formatted.append(name)
        if len(authors) > 6:
            formatted.append("et al.")
        return ", ".join(formatted)

    journal_str = f"{journal}. " if journal else ""
    doi_str     = f" {doi_url}" if doi_url else ""

    if style == "apa7":
        return (
            f"{_surnames_initials(authors)} ({year}). "
            f"{title}. {journal_str}{doi_str}"
        ).strip()

    elif style == "harvard":
        return (
            f"{_surnames_initials(authors)} ({year}) "
            f"'{title}', {journal_str}{doi_str}"
        ).strip()

    elif style == "ieee":
        return (
            f"[{number}] {_initials_surname(authors)}, "
            f'"{title}," {journal_str}{year}.{doi_str}'
        ).strip()

    elif style == "vancouver":
        return (
            f"{number}. {_initials_surname(authors)}. "
            f"{title}. {journal_str}{year}.{doi_str}"
        ).strip()

    elif style == "chicago":
        return (
            f"{_surnames_initials(authors)}. "
            f'"{title}." {journal_str}({year}).{doi_str}'
        ).strip()

    elif style == "mla":
        return (
            f"{_surnames_initials(authors)}. "
            f'"{title}." {journal_str}{year}.{doi_str}'
        ).strip()

    # Default APA
    return (
        f"{_surnames_initials(authors)} ({year}). "
        f"{title}. {journal_str}{doi_str}"
    ).strip()


# ─── BUILD FULL REFERENCE LIST STRING ─────────────────────────────────────────

def build_reference_list_text(papers: list[dict], style: str) -> str:
    """
    Build the complete formatted reference list as plain text.
    Used at the end of Chapter 2 and in the PDF.

    For numbered styles (IEEE, Vancouver), numbers are assigned
    in order of appearance.
    """
    print(f"[citation] build_reference_list_text: {len(papers)} papers, style={style}")
    if not papers:
        return "No verified references available."

    from utils.constants import REFERENCE_HEADINGS
    heading = REFERENCE_HEADINGS.get(style, "References")

    # Sort alphabetically for author-date styles
    numbered_styles = {"ieee", "vancouver"}
    if style not in numbered_styles:
        papers = sorted(
            papers,
            key=lambda p: (
                p.get("authors", [""])[0].strip().split()[-1].lower()
                if p.get("authors") else "zzz"
            ),
        )

    lines = [f"{heading.upper()}\n"]
    for i, paper in enumerate(papers, 1):
        entry = format_full_reference(paper, style, number=i)
        if entry:
            lines.append(entry)

    return "\n\n".join(lines)


# ─── DEDUPLICATE REFERENCES ───────────────────────────────────────────────────

def deduplicate_references(papers: list[dict]) -> list[dict]:
    """
    Remove duplicate papers by DOI.
    Keeps the first occurrence of each DOI.
    """
    print(f"[citation] deduplicate_references: input={len(papers)}")
    seen_dois  = set()
    seen_titles = set()
    unique = []

    for paper in papers:
        doi   = paper.get("doi", "").strip().lower()
        title = paper.get("title", "").strip().lower()[:80]

        if doi and doi in seen_dois:
            continue
        if title and title in seen_titles:
            continue

        if doi:
            seen_dois.add(doi)
        if title:
            seen_titles.add(title)

        unique.append(paper)

    print(f"[citation] After dedup: {len(unique)} unique papers")
    return unique


# ─── SCORE AND RANK CITATIONS ─────────────────────────────────────────────────

def rank_citations(papers: list[dict], topic: str) -> list[dict]:
    """
    Score and rank citations by relevance and quality.
    Prioritises:
    - Papers with high citation counts (more established)
    - More recent papers (post-2015)
    - Papers from reputable journals
    - Papers with Nigerian/African context in title
    """
    print(f"[citation] rank_citations: {len(papers)} papers")
    topic_lower = topic.lower()
    nigerian_keywords = [
        "nigeria", "nigerian", "africa", "african", "west africa",
        "lagos", "abuja", "kano", "developing", "emerging market",
    ]

    def score(paper: dict) -> float:
        s = 0.0
        # Citation count score (log scale)
        cited = paper.get("cited_by", 0) or 0
        if cited > 0:
            import math
            s += min(math.log(cited + 1) * 2, 10)

        # Recency score
        year = paper.get("year")
        if year:
            try:
                age = 2025 - int(year)
                s += max(0, 10 - age * 0.5)
            except Exception:
                pass

        # Nigerian context bonus
        title_lower = paper.get("title", "").lower()
        for kw in nigerian_keywords:
            if kw in title_lower:
                s += 5
                break

        # Topic relevance (simple keyword overlap)
        topic_words = set(topic_lower.split())
        title_words = set(title_lower.split())
        overlap = len(topic_words & title_words)
        s += overlap * 1.5

        # Has DOI bonus
        if paper.get("doi"):
            s += 2

        return s

    ranked = sorted(papers, key=score, reverse=True)
    print(f"[citation] Top paper: {ranked[0].get('title', '')[:60] if ranked else 'none'}")
    return ranked


# ─── FULL CITATION PIPELINE FOR CHAPTER 2 ────────────────────────────────────

async def run_chapter_2_citation_pipeline(
    brief: dict,
    queries: list[str],
    telegram_id: int,
) -> dict:
    """
    Complete citation pipeline for Chapter 2.
    Searches, deduplicates, ranks, saves to DB, and returns
    everything Chapter 2 needs.

    Returns:
        {
            "papers":          [...],     # ranked, deduped citation list
            "reference_list":  "...",     # formatted reference list text
            "total_found":     N,
            "source":          "openalex|crossref|...",
        }
    """
    print(f"[citation] run_chapter_2_citation_pipeline: {len(queries)} queries")

    # Run batch search
    raw_papers = await find_citations_batch(queries, max_per_query=5)
    print(f"[citation] Raw papers found: {len(raw_papers)}")

    if not raw_papers:
        print("[citation] No papers found — returning empty")
        return {
            "papers":         [],
            "reference_list": "",
            "total_found":    0,
            "source":         "none",
        }

    # Deduplicate
    papers = deduplicate_references(raw_papers)

    # Rank by relevance
    topic  = brief.get("topic", "")
    papers = rank_citations(papers, topic)

    # Take top 20 — enough for a thorough literature review
    papers = papers[:20]
    print(f"[citation] Final citation count: {len(papers)}")

    # Save each to Supabase
    for paper in papers:
        add_verified_reference(telegram_id, paper)

    # Build reference list text
    style          = brief.get("citation_style", "apa7")
    reference_list = build_reference_list_text(papers, style)

    # Determine primary source
    sources = [p.get("source", "unknown") for p in papers]
    primary_source = max(set(sources), key=sources.count) if sources else "none"

    return {
        "papers":         papers,
        "reference_list": reference_list,
        "total_found":    len(papers),
        "source":         primary_source,
    }


print("[citation_service.py] Citation service loaded.")