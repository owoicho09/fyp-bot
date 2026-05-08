print("[chapter_2.py] Loading Chapter 2 prompt builder...")


def get_chapter_2_prompt(brief: dict, citations: list[dict]) -> str:
    """
    Build the user-turn prompt for Chapter 2: Review of Related Literature.
    This is the most citation-intensive chapter. Every claim must be backed
    by a real verified paper from the citations list provided.
    Claude must NEVER invent citations — only use what is in the list.
    """
    print(f"[chapter_2] Building prompt. Citations available: {len(citations)}")

    topic            = brief.get("topic", "")
    research_question= brief.get("research_question", "")
    department       = brief.get("department", "")
    university       = brief.get("university", "")
    citation_style   = brief.get("citation_style", "apa7")
    research_type    = brief.get("research_type", "quantitative")
    objectives       = brief.get("objectives", [])
    nigerian_context = brief.get("nigerian_context", "")

    # Format citations for injection into the prompt
    citations_text = _format_citations_for_prompt(citations)

    # Format objectives for cross-reference
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
Ensure Nigerian studies and context appear throughout the review, not just in one section.
"""

    return f"""Write a complete, publication-quality Chapter 2 (Review of Related Literature) for this final year project:

TOPIC: {topic}
RESEARCH QUESTION: {research_question}
DEPARTMENT: {department}
UNIVERSITY: {university}
CITATION STYLE: {citation_style.upper()}
RESEARCH DESIGN: {research_type}

{objectives_text}
{nigerian_instruction}

VERIFIED CITATIONS AVAILABLE — USE ONLY THESE:
{citations_text}

ABSOLUTE CITATION RULES:
1. You may ONLY cite papers from the list above — every author name, year, journal, and DOI must match exactly
2. NEVER invent, guess, or approximate a citation — if you cannot find a suitable paper in the list, write the claim without a citation and add [CITATION NEEDED] so the student knows to find one manually
3. Do not use the same citation more than 3 times in the chapter
4. Aim to use at least 70% of the provided citations
5. For in-text citations use {citation_style.upper()} format exactly

CHAPTER 2 MUST CONTAIN ALL OF THESE SECTIONS IN ORDER:

2.1 INTRODUCTION
- Brief paragraph introducing the chapter and explaining its organisation
- State the key themes the review will cover

2.2 CONCEPTUAL FRAMEWORK
- Define and discuss the key concepts central to this study (minimum 3 concepts)
- For each concept: provide a working definition, trace its evolution in literature, and explain how it applies to this study
- Use multiple citations to show different scholarly perspectives on each concept
- Minimum 400 words

2.3 THEORETICAL FRAMEWORK
- Identify 1–2 theories that underpin this study
- For each theory: name it, identify its originator and year, explain its core propositions, and justify why it is relevant to this study
- Critique the theory — mention its limitations and how this study addresses or works within those limitations
- Minimum 300 words

2.4 EMPIRICAL REVIEW
- Review at least 8–10 published empirical studies directly related to this topic
- For each study reviewed: state the author(s) and year, the objective of the study, methodology used, findings, and relevance to the current study
- Organise thematically — not as a list, but as flowing academic prose that builds an argument
- Include studies from Nigerian/African context AND international studies
- Show agreements and contradictions between different studies
- Minimum 800 words

2.5 REVIEW OF RELATED STUDIES IN NIGERIA
- Focus specifically on Nigerian studies related to this topic
- If Nigerian studies are sparse, discuss African regional studies and explain the gap
- Reference specific Nigerian institutions, sectors, or policies studied
- Minimum 300 words

2.6 GAP IN LITERATURE
- Synthesise what the reviewed literature reveals collectively
- Clearly identify 2–3 specific gaps in the existing literature that this study fills
- Gaps should be logical — emerging directly from what was reviewed
- This section justifies the existence of this study
- Minimum 200 words

2.7 SUMMARY OF CHAPTER TWO
- One paragraph summarising the key themes reviewed
- Transitional sentence leading into Chapter 3

REFERENCE LIST FOR THIS CHAPTER:
At the end of Chapter 2, include a properly formatted reference list of ALL papers cited in this chapter.
Format every entry in {citation_style.upper()} style exactly.
Use this data for each reference:
{citations_text}

WRITING QUALITY REQUIREMENTS:
- The literature review must read as a coherent argument, not a list of summaries
- Use synthesis: "While Adeyemi (2020) found X, this contradicts Okafor (2022) who argued Y..."
- Use transitional phrases between paragraphs and sections
- Show critical thinking — do not just describe studies, evaluate them
- Vary citation integration: sometimes name the author first, sometimes use parenthetical citations
- Minimum total chapter length: 2,500 words (excluding reference list)

Write the full chapter now. Do not summarise or truncate any section."""


def _format_citations_for_prompt(citations: list[dict]) -> str:
    """Format the citations list into a readable block for the prompt."""
    if not citations:
        return "NO CITATIONS PROVIDED — Write claims without citations and mark each with [CITATION NEEDED]"

    lines = [f"Total citations available: {len(citations)}\n"]
    for i, c in enumerate(citations, 1):
        authors = ", ".join(c.get("authors", [])[:3])
        if len(c.get("authors", [])) > 3:
            authors += " et al."
        lines.append(
            f"[{i}] Authors: {authors or 'Unknown'}\n"
            f"     Year: {c.get('year', 'n.d.')}\n"
            f"     Title: {c.get('title', 'Unknown')}\n"
            f"     Journal: {c.get('journal', 'Unknown')}\n"
            f"     DOI: {c.get('doi', 'No DOI')}\n"
            f"     Cited by: {c.get('cited_by', 0)} papers\n"
        )
    return "\n".join(lines)


print("[chapter_2.py] Chapter 2 prompt builder loaded.")