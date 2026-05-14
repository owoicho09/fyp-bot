print("[chapter_1.py] Loading Chapter 1 prompt builder...")


def get_chapter_1_prompt(brief: dict) -> str:
    print(f"[chapter_1] Building prompt for: {brief.get('topic', '')[:60]}")

    topic            = brief.get("topic", "")
    research_question= brief.get("research_question", "")
    population       = brief.get("population", "")
    time_frame       = brief.get("time_frame", "")
    department       = brief.get("department", "") or ""
    university       = brief.get("university", "")
    level            = brief.get("academic_level", "bsc") or "bsc"
    research_type    = brief.get("research_type", "quantitative") or "quantitative"
    citation_style   = brief.get("citation_style", "apa7") or "apa7"
    nigerian_context = brief.get("nigerian_context", "")
    student_bg       = brief.get("student_background", "")
    supervisor_notes = brief.get("supervisor_context", "")
    chapter_format   = brief.get("chapter_format", "")
    outline          = brief.get("chapter_1_outline", "")

    scope_text = ""
    if population:
        scope_text += f"The study focuses on: {population}. "
    if time_frame:
        scope_text += f"The time frame is: {time_frame}. "

    # Outline injection — student's structure takes priority
    outline_injection = ""
    if outline:
        outline_injection = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STUDENT'S OUTLINE FOR THIS CHAPTER
Follow this structure exactly. It takes priority over the standard sections below.
Fill any gaps with appropriate standard content.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{outline}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # Custom chapter format from student's university
    format_injection = ""
    if chapter_format:
        format_injection = f"""
UNIVERSITY-SPECIFIC FORMAT:
This student's university uses these specific section headings.
Use them instead of the generic ones where applicable:
{chapter_format}
"""

    background_injection = ""
    if student_bg:
        background_injection = f"""
STUDENT'S OWN KNOWLEDGE — weave this in to make it sound authentic:
"{student_bg}"
"""

    nigerian_injection = ""
    if nigerian_context:
        nigerian_injection = f"""
NIGERIAN-SPECIFIC CONTEXT THE STUDENT MENTIONED:
{nigerian_context}
Make these details appear naturally throughout the chapter.
"""

    supervisor_injection = ""
    if supervisor_notes:
        supervisor_injection = f"""
SUPERVISOR/FORMAT REQUIREMENTS:
{supervisor_notes}
"""

    hypothesis_instruction = _get_hypothesis_instruction(research_type, department)

    return f"""Write a complete, publication-quality Chapter 1 (Introduction) for this final year project.
{outline_injection}
{format_injection}
TOPIC: {topic}
CORE RESEARCH QUESTION: {research_question}
DEPARTMENT: {department}
UNIVERSITY: {university}
SCOPE: {scope_text}
CITATION STYLE: {citation_style.upper()}
{background_injection}
{nigerian_injection}
{supervisor_injection}

STANDARD CHAPTER 1 SECTIONS (use these if no outline was provided above):

1.1 BACKGROUND TO THE STUDY
- Open with the global context of the topic (2-3 paragraphs)
- Narrow to the African/West African context (1-2 paragraphs)
- Narrow further to the Nigerian context with specific data, statistics, or policy references (2-3 paragraphs)
- Close with the specific gap this study addresses (1 paragraph)
- Cite at least 3 Nigerian data sources (CBN, NBS, INEC, NCDC, NPC, or relevant ministry reports)
- Minimum 600 words

1.2 STATEMENT OF THE PROBLEM
- Clearly articulate the specific problem the study addresses
- Use evidence to show the problem exists
- State the consequences of leaving this problem unaddressed
- End with a clear problem statement sentence
- Minimum 250 words

1.3 OBJECTIVES OF THE STUDY
- State the general objective (1 sentence)
- List 4-5 specific objectives, each starting with an action verb
- Objectives must directly address the research question and be measurable

1.4 RESEARCH QUESTIONS
- Generate 4-5 research questions corresponding to each specific objective
- Each must be answerable through the chosen research design ({research_type})

{hypothesis_instruction}

1.6 SIGNIFICANCE OF THE STUDY
- Theoretical significance (contribution to academic knowledge)
- Practical significance (benefit to practitioners, policymakers, organisations)
- Significance to Nigerian society/economy/sector
- Minimum 200 words

1.7 SCOPE OF THE STUDY
- Geographical scope (specific Nigerian state/city/institution)
- Subject scope (what is covered and excluded)
- Time scope ({time_frame if time_frame else 'specify an appropriate time range'})

1.8 LIMITATIONS OF THE STUDY
- 3-4 genuine, realistic limitations
- For each: explain how it was mitigated or why it does not invalidate the findings

1.9 DEFINITION OF TERMS
- Define 6-8 key terms operationally (how used IN THIS STUDY)
- Cite sources for theoretical definitions

1.10 ORGANISATION OF THE STUDY
- One paragraph describing what each of the 5 chapters covers
- Written in future tense

CRITICAL: The objectives, research questions, and hypotheses you write here are BINDING
across all subsequent chapters. Make them coherent and measurable.

At the end of this chapter output this JSON block exactly:
<!--EXTRACTED_DATA
{{
  "objectives": ["objective 1", "objective 2", "objective 3", "objective 4", "objective 5"],
  "research_questions": ["question 1", "question 2", "question 3", "question 4", "question 5"],
  "hypotheses": ["H01: ...", "H02: ...", "H03: ..."]
}}
EXTRACTED_DATA-->

Write the full chapter now. Do not summarise or truncate any section."""


def _get_hypothesis_instruction(research_type: str, department: str) -> str:
    dept_lower = (department or "").lower()

    if (research_type or "").lower() == "qualitative":
        return """1.5 RESEARCH HYPOTHESES
- State 2-3 research propositions instead of null hypotheses
- Frame as: "It is proposed that..." or "This study proposes that..."
- Each proposition should be testable through qualitative methods"""

    if any(d in dept_lower for d in ["account", "finance", "banking", "economics"]):
        return """1.5 RESEARCH HYPOTHESES
- State 3-4 formal null and alternate hypotheses
- H01 (Null): State the null position
- Hi1 (Alternate): State the alternate position
- Each must correspond to a specific objective
- Must be testable with statistical tools (regression, correlation, ANOVA)"""

    return """1.5 RESEARCH HYPOTHESES
- State 3-4 null and alternate hypotheses
- H01: [Null — states no significant relationship/effect]
- H11: [Alternate — states a significant relationship/effect exists]
- Each must correspond to a specific research objective"""


print("[chapter_1.py] Chapter 1 prompt builder loaded.")