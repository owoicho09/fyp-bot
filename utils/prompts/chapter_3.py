print("[chapter_3.py] Loading Chapter 3 prompt builder...")


def get_chapter_3_prompt(brief: dict) -> str:
    print(f"[chapter_3] Building prompt for: {brief.get('topic', '')[:60]}")

    topic          = brief.get("topic", "")
    population     = brief.get("population", "")
    time_frame     = brief.get("time_frame", "")
    research_type  = brief.get("research_type", "quantitative") or "quantitative"
    department     = brief.get("department", "") or ""
    university     = brief.get("university", "")
    citation_style = brief.get("citation_style", "apa7") or "apa7"
    objectives     = brief.get("objectives", [])
    nigerian_ctx   = brief.get("nigerian_context", "")
    chapter_format = brief.get("chapter_format", "")
    outline        = brief.get("chapter_3_outline", "")

    objectives_text = ""
    if objectives:
        objectives_text = "OBJECTIVES FROM CHAPTER 1 (methodology must align with all of these):\n"
        for i, obj in enumerate(objectives, 1):
            objectives_text += f"{i}. {obj}\n"

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

    design_instructions = _get_design_instructions(research_type, department)

    return f"""Write a complete, publication-quality Chapter 3 (Research Methodology) for this final year project.
{outline_injection}
{format_injection}
TOPIC: {topic}
RESEARCH DESIGN: {research_type.upper()}
POPULATION/SCOPE: {population}
TIME FRAME: {time_frame}
DEPARTMENT: {department}
UNIVERSITY: {university}
CITATION STYLE: {citation_style.upper()}
NIGERIAN CONTEXT: {nigerian_ctx}

{objectives_text}
{design_instructions}

STANDARD CHAPTER 3 SECTIONS (use if no outline provided above):

3.1 INTRODUCTION
- Brief paragraph introducing the chapter
- State this chapter describes the methods used to achieve the study objectives

3.2 RESEARCH DESIGN
- Name and define the research design ({research_type})
- Cite at least 2 methodology authors (Creswell, Kothari, Saunders, Bryman)
- Justify why this design suits this specific study
- Mention the philosophical underpinning (positivism/interpretivism)

3.3 AREA OF STUDY
- Describe the specific geographical area, institution, or organisation
- Include relevant background (population size, economic profile, why chosen)
- Must reference the specific Nigerian location: {population}

3.4 POPULATION OF THE STUDY
- Define the target population precisely
- State total population size with source if available
- Distinguish target population from accessible population

3.5 SAMPLE SIZE AND SAMPLING TECHNIQUE
- Determine sample size using appropriate formula
- Quantitative: use Taro Yamane or Cochran formula — show calculation with actual numbers
- Qualitative: justify purposive/snowball/theoretical sampling
- State the final sample size clearly

3.6 INSTRUMENT FOR DATA COLLECTION
- Describe the primary instrument
- Describe structure (sections, number of items, scale used)
- For questionnaires: specify Likert scale (e.g. 5-point: Strongly Agree to Strongly Disagree)
- Justify why this instrument suits the research design

3.7 VALIDITY OF THE INSTRUMENT
- Explain how content validity was established
- Explain face validity if applicable
- Mention construct validity for quantitative studies

3.8 RELIABILITY OF THE INSTRUMENT
- Quantitative: Cronbach's Alpha threshold (0.7 or above)
- State a pilot study was conducted (10-15% of main sample)
- State the Cronbach's Alpha obtained
- Qualitative: discuss trustworthiness (credibility, transferability, dependability, confirmability)

3.9 METHOD OF DATA COLLECTION
- Describe how instruments were administered
- Describe how respondents were reached in Nigerian context
- Mention ethical considerations (anonymity, informed consent, voluntary participation)

3.10 METHOD OF DATA ANALYSIS
- State statistical tools for each research question/hypothesis
- Quantitative: descriptive statistics, inferential statistics matched to hypotheses
- Qualitative: thematic analysis, content analysis, or narrative analysis
- State software (SPSS v23+, Excel, or Atlas.ti)
- Explain hypothesis testing (significance level: p < 0.05)

3.11 ETHICAL CONSIDERATIONS
- Informed consent, confidentiality, voluntary participation, data storage

WRITING REQUIREMENTS:
- Every methodological choice must be justified — not just described
- Cite methodology authors for key decisions
- Sampling calculation must show actual numbers
- Be specific about Nigerian context throughout
- Minimum 1,800 words

Write the full chapter now. Do not summarise or truncate any section."""


def _get_design_instructions(research_type: str, department: str) -> str:
    research_type = (research_type or "quantitative").lower()
    dept_lower    = (department or "").lower()

    if research_type == "qualitative":
        return """QUALITATIVE DESIGN INSTRUCTIONS:
- Instrument is an interview guide or focus group guide — not a questionnaire
- Sample size is smaller (10-30 participants) justified by saturation
- Data analysis uses thematic analysis — describe the 6-step Braun & Clarke process
- Validity discussed as trustworthiness
- No statistical hypothesis testing — use research propositions"""

    if research_type == "mixed":
        return """MIXED METHODS DESIGN INSTRUCTIONS:
- Explain whether design is sequential exploratory, explanatory, or concurrent triangulation
- Describe both quantitative and qualitative strands separately
- Explain how the two strands are integrated
- Justify why mixed approach is superior to either alone"""

    if any(d in dept_lower for d in ["account", "finance", "banking", "economics"]):
        return """ACCOUNTING/FINANCE INSTRUCTIONS:
- Use ex-post facto or survey research design
- For secondary data: describe sources (CBN annual reports, NSE data, company reports)
- Specify panel data or time series if applicable
- Hypotheses tested with regression or correlation
- Specify OLS regression or Pearson correlation"""

    if any(d in dept_lower for d in ["computer", "software", "engineering", "technology"]):
        return """ENGINEERING/CS INSTRUCTIONS:
- Describe system development methodology if applicable (Agile, Waterfall, SDLC)
- For experimental designs: describe setup and control variables
- If building a system: describe development tools, programming languages, testing methodology"""

    return ""


print("[chapter_3.py] Chapter 3 prompt builder loaded.")