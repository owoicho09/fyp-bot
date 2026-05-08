print("[chapter_1.py] Loading Chapter 1 prompt builder...")


def get_chapter_1_prompt(brief: dict) -> str:
    """
    Build the user-turn prompt for Chapter 1: Introduction.
    Chapter 1 establishes the entire project — objectives, research questions,
    and hypotheses set here must remain consistent across all subsequent chapters.
    """
    print(f"[chapter_1] Building prompt for topic: {brief.get('topic', '')[:60]}")

    topic            = brief.get("topic", "")
    research_question= brief.get("research_question", "")
    population       = brief.get("population", "")
    time_frame       = brief.get("time_frame", "")
    department       = brief.get("department", "")
    university       = brief.get("university", "")
    level            = brief.get("academic_level", "bsc")
    research_type    = brief.get("research_type", "quantitative")
    citation_style   = brief.get("citation_style", "apa7")
    nigerian_context = brief.get("nigerian_context", "")
    student_bg       = brief.get("student_background", "")
    supervisor_notes = brief.get("supervisor_context", "")

    # Hypothesis instruction depends on research type and department
    hypothesis_instruction = _get_hypothesis_instruction(research_type, department)

    # Scope instruction
    scope_text = ""
    if population:
        scope_text += f"The study focuses on: {population}. "
    if time_frame:
        scope_text += f"The time frame is: {time_frame}. "

    # Student background injection
    background_injection = ""
    if student_bg:
        background_injection = f"""
STUDENT'S OWN KNOWLEDGE TO WEAVE IN:
The student shared this context about their topic — use their perspective and knowledge
to make the Background to Study sound authentic and personally grounded:
"{student_bg}"
"""

    nigerian_injection = ""
    if nigerian_context:
        nigerian_injection = f"""
NIGERIAN-SPECIFIC CONTEXT THE STUDENT MENTIONED:
{nigerian_context}
Make sure these specific details appear naturally in the chapter.
"""

    supervisor_injection = ""
    if supervisor_notes:
        supervisor_injection = f"""
SUPERVISOR/FORMAT REQUIREMENTS:
{supervisor_notes}
Ensure these requirements are reflected in the structure and formatting.
"""

    return f"""Write a complete, publication-quality Chapter 1 (Introduction) for the following final year research project:

TOPIC: {topic}
CORE RESEARCH QUESTION: {research_question}
DEPARTMENT: {department}
UNIVERSITY: {university}
SCOPE: {scope_text}
CITATION STYLE: {citation_style.upper()}
{background_injection}
{nigerian_injection}
{supervisor_injection}

CHAPTER 1 MUST CONTAIN ALL OF THESE SECTIONS IN ORDER:

1.1 BACKGROUND TO THE STUDY
- Open with the global context of the topic (2–3 paragraphs)
- Narrow down to the African/West African context (1–2 paragraphs)
- Narrow further to the Nigerian context with specific Nigerian data, statistics, or policy references (2–3 paragraphs)
- Close with the specific gap this study addresses (1 paragraph)
- Cite at least 3 Nigerian data sources (CBN, NBS, INEC, NCDC, NPC, or relevant ministry reports)
- Minimum 600 words for this section

1.2 STATEMENT OF THE PROBLEM
- Clearly articulate the specific problem the study addresses
- Use evidence to show the problem exists (statistics, documented issues, policy failures)
- State the consequences of leaving this problem unaddressed
- End with a clear problem statement sentence
- Minimum 250 words

1.3 OBJECTIVES OF THE STUDY
- State the general objective (1 sentence)
- List 4–5 specific objectives, each starting with an action verb (To examine, To assess, To determine, To evaluate, To investigate)
- Objectives must directly address the research question and be measurable

1.4 RESEARCH QUESTIONS
- Generate 4–5 research questions that directly correspond to each specific objective
- Each question must be answerable through the chosen research design ({research_type})
- Questions must be specific, not general

{hypothesis_instruction}

1.6 SIGNIFICANCE OF THE STUDY
- Explain the theoretical significance (contribution to academic knowledge)
- Explain the practical significance (benefit to practitioners, policymakers, organisations)
- Explain the significance to Nigerian society/economy/sector
- Mention specific beneficiaries: students, policymakers, organisations, future researchers
- Minimum 200 words

1.7 SCOPE OF THE STUDY
- Define the geographical scope (specific Nigerian state/city/institution)
- Define the subject scope (what aspects are covered and what are excluded)
- Define the time scope ({time_frame if time_frame else 'specify an appropriate time range'})
- Explain briefly why these boundaries were chosen

1.8 LIMITATIONS OF THE STUDY
- List 3–4 genuine, realistic limitations (not just generic statements)
- For each limitation, explain how it was mitigated or why it does not invalidate the findings
- Common realistic limitations for Nigerian research: limited access to respondents, time constraints, respondents' reluctance, limited secondary data

1.9 DEFINITION OF TERMS
- Define 6–8 key terms/concepts used in this study
- Definitions must be operational (how the term is used IN THIS STUDY, not just dictionary definitions)
- Cite sources for theoretical definitions

1.10 ORGANISATION OF THE STUDY
- One paragraph describing what each of the 5 chapters covers
- Written in future tense ("Chapter Two reviews...", "Chapter Three describes...")

CRITICAL REQUIREMENTS:
- The objectives, research questions, and hypotheses you write in this chapter are BINDING — they will be used in Chapters 3, 4, and 5. Make them coherent, measurable, and appropriate for the research design.
- At the end of this chapter, add a JSON block in this exact format so the system can extract and store the objectives and hypotheses:

<!--EXTRACTED_DATA
{{
  "objectives": ["objective 1", "objective 2", "objective 3", "objective 4", "objective 5"],
  "research_questions": ["question 1", "question 2", "question 3", "question 4", "question 5"],
  "hypotheses": ["H01: ...", "H02: ...", "H03: ..."]
}}
EXTRACTED_DATA-->

Write the full chapter now. Do not summarise or truncate any section."""


def _get_hypothesis_instruction(research_type: str, department: str) -> str:
    """Return the appropriate hypothesis section instruction based on research type."""

    if research_type == "qualitative":
        return """1.5 RESEARCH HYPOTHESES
- For qualitative research, state 2–3 research propositions instead of null hypotheses
- Frame as: "It is proposed that..." or "This study proposes that..."
- Each proposition should be testable through qualitative methods (interviews, focus groups, etc.)"""

    # Quantitative or mixed methods — formal null/alternate hypotheses
    dept_lower = department.lower()
    if any(d in dept_lower for d in ["account", "finance", "banking", "economics"]):
        return """1.5 RESEARCH HYPOTHESES
- State 3–4 formal null and alternate hypotheses in standard format
- H₀₁ (Null hypothesis): State the null position
- Hᵢ₁ (Alternate hypothesis): State the alternate position
- Each hypothesis must correspond directly to a specific objective
- For accounting/finance studies: hypotheses must be testable with statistical tools (regression, correlation, ANOVA)
- Use formal notation: H₀ for null, Hᵢ or H₁ for alternate"""

    return """1.5 RESEARCH HYPOTHESES
- State 3–4 null and alternate hypotheses
- H₀₁: [Null hypothesis — states no significant relationship/effect]
- H₁₁: [Alternate hypothesis — states a significant relationship/effect exists]
- Each hypothesis must correspond to a specific research objective
- Hypotheses must be testable with the chosen research design"""


print("[chapter_1.py] Chapter 1 prompt builder loaded.")