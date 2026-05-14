print("[chapter_2.py] Loading Chapter 2 prompt builder...")


def get_chapter_2_prompt(brief: dict, citations: list[dict]) -> str:
    print(f"[chapter_2] Building prompt. Citations: {len(citations)}")

    topic             = brief.get("topic", "")
    research_question = brief.get("research_question", "")
    department        = brief.get("department", "")
    university        = brief.get("university", "")
    citation_style    = brief.get("citation_style", "apa7") or "apa7"
    research_type     = brief.get("research_type", "quantitative") or "quantitative"
    objectives        = brief.get("objectives", [])
    nigerian_context  = brief.get("nigerian_context", "")
    citation_year_from = brief.get("citation_year_from", 2019)
    chapter_format    = brief.get("chapter_format", "")
    outline           = brief.get("chapter_2_outline", "")

    citations_text = _format_citations_for_prompt(citations)

    objectives_text = ""
    if objectives:
        objectives_text = "OBJECTIVES FROM CHAPTER 1 (literature review must address each one):\n"
        for i, obj in enumerate(objectives, 1):
            objectives_text += f"{i}. {obj}\n"

    nigerian_instruction = ""
    if nigerian_context:
        nigerian_instruction = f"""
NIGERIAN CONTEXT TO INCORPORATE:
{nigerian_context}
Nigerian studies and context must appear throughout, not just in one section.
"""

    outline_injection = ""
    if outline:
        outline_injection = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STUDENT'S OUTLINE FOR THIS CHAPTER
Follow this structure exactly. It takes priority over the standard sections below.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{outline}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    format_injection = ""
    if chapter_format:
        format_injection = f"""
UNIVERSITY-SPECIFIC FORMAT:
{chapter_format}
"""

    year_note = (
        f"Citations provided are from {citation_year_from} onwards as requested by the student."
        if citation_year_from > 1990
        else "Citations from any year are acceptable for this student."
    )

    return f"""Write a complete, publication-quality Chapter 2 (Review of Related Literature) for this final year project.
{outline_injection}
{format_injection}
TOPIC: {topic}
RESEARCH QUESTION: {research_question}
DEPARTMENT: {department}
UNIVERSITY: {university}
CITATION STYLE: {citation_style.upper()}
RESEARCH DESIGN: {research_type}
CITATION YEAR NOTE: {year_note}

{objectives_text}
{nigerian_instruction}

VERIFIED CITATIONS — USE ONLY THESE. NEVER INVENT A CITATION:
{citations_text}

ABSOLUTE CITATION RULES:
1. Only cite papers from the list above — author, year, journal, DOI must match exactly
2. If no suitable paper exists in the list, write the claim without a citation and add [CITATION NEEDED]
3. Do not use the same citation more than 3 times
4. Use at least 70% of the provided citations
5. Use {citation_style.upper()} format exactly throughout

STANDARD CHAPTER 2 SECTIONS (use if no outline provided above):

2.1 INTRODUCTION
- Brief paragraph introducing the chapter and its organisation
- State the key themes the review will cover

2.2 CONCEPTUAL FRAMEWORK
- Define and discuss the key concepts central to this study (minimum 3 concepts)
- For each: working definition, evolution in literature, application to this study
- Use multiple citations showing different scholarly perspectives
- Minimum 400 words

2.3 THEORETICAL FRAMEWORK
- Identify 1-2 theories that underpin this study
- For each: name, originator and year, core propositions, relevance to this study
- Critique the theory — limitations and how this study works within them
- Minimum 300 words

2.4 EMPIRICAL REVIEW
- Review at least 8-10 published empirical studies directly related to this topic
- For each: author(s) and year, objective, methodology, findings, relevance
- Organise thematically as flowing academic prose — not a list
- Include Nigerian/African studies AND international studies
- Show agreements and contradictions between studies
- Minimum 800 words

2.5 REVIEW OF RELATED STUDIES IN NIGERIA
- Focus specifically on Nigerian studies
- If sparse, discuss African regional studies and explain the gap
- Reference specific Nigerian institutions, sectors, or policies
- Minimum 300 words

2.6 GAP IN LITERATURE
- Synthesise what the literature reveals collectively
- Identify 2-3 specific gaps this study fills
- Gaps must emerge logically from what was reviewed
- Minimum 200 words

2.7 SUMMARY OF CHAPTER TWO
- One paragraph summarising key themes reviewed
- Transitional sentence to Chapter 3

REFERENCE LIST:
At the end include a properly formatted reference list of all cited papers in {citation_style.upper()} style.

WRITING QUALITY:
- Literature review must read as a coherent argument not a list of summaries
- Synthesise: "While Adeyemi (2020) found X, this contradicts Okafor (2022) who argued Y..."
- Show critical thinking — evaluate studies, do not just describe them
- Vary citation integration — sometimes author-first, sometimes parenthetical
- Minimum 2,500 words excluding reference list

Write the full chapter now. Do not summarise or truncate any section."""


def _format_citations_for_prompt(citations: list[dict]) -> str:
    if not citations:
        return "NO CITATIONS PROVIDED — Write claims without citations and mark each with [CITATION NEEDED]"

    lines = [f"Total citations available: {len(citations)}\n"]
    for i, c in enumerate(citations, 1):
        authors = ", ".join(c.get("authors", [])[:3])
        if len(c.get("authors", [])) > 3:
            authors += " et al."
        year = c.get('year', 'n.d.')
        lines.append(
            f"[{i}] Authors: {authors or 'Unknown'}\n"
            f"     Year: {year}\n"
            f"     Title: {c.get('title', 'Unknown')}\n"
            f"     Journal: {c.get('journal', 'Unknown')}\n"
            f"     DOI: {c.get('doi', 'No DOI')}\n"
            f"     Cited by: {c.get('cited_by', 0)} papers\n"
        )
    return "\n".join(lines)


print("[chapter_2.py] Chapter 2 prompt builder loaded.")