print("[chapter_3.py] Loading Chapter 3 prompt builder...")


def get_chapter_3_prompt(brief: dict) -> str:
    """
    Build the user-turn prompt for Chapter 3: Research Methodology.
    Must be consistent with the research design, population, and objectives
    established in Chapter 1.
    """
    print(f"[chapter_3] Building prompt for: {brief.get('topic', '')[:60]}")

    topic          = brief.get("topic", "")
    population     = brief.get("population", "")
    time_frame     = brief.get("time_frame", "")
    research_type  = brief.get("research_type", "quantitative")
    department     = brief.get("department", "")
    university     = brief.get("university", "")
    citation_style = brief.get("citation_style", "apa7")
    objectives     = brief.get("objectives", [])
    nigerian_ctx   = brief.get("nigerian_context", "")

    objectives_text = ""
    if objectives:
        objectives_text = "OBJECTIVES FROM CHAPTER 1 (methodology must align with all of these):\n"
        for i, obj in enumerate(objectives, 1):
            objectives_text += f"{i}. {obj}\n"

    design_instructions = _get_design_instructions(research_type, department)

    return f"""Write a complete, publication-quality Chapter 3 (Research Methodology) for this final year project:

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

CHAPTER 3 MUST CONTAIN ALL OF THESE SECTIONS IN ORDER:

3.1 INTRODUCTION
- Brief paragraph introducing the chapter
- State that this chapter describes the methods used to achieve the study objectives

3.2 RESEARCH DESIGN
- Name and define the research design adopted ({research_type})
- Cite at least 2 methodology authors who define/describe this design (e.g. Creswell, Kothari, Saunders, Bryman)
- Justify why this design is appropriate for this specific study
- Mention the philosophical underpinning (positivism for quantitative, interpretivism for qualitative)

3.3 AREA OF STUDY
- Describe the specific geographical area, institution, or organisation being studied
- Include relevant background about the study area (population size, economic profile, why it was chosen)
- Must reference specific Nigerian location from the student's scope: {population}

3.4 POPULATION OF THE STUDY
- Define the target population precisely
- State the total population size with a source if available
- Distinguish between target population and accessible population

3.5 SAMPLE SIZE AND SAMPLING TECHNIQUE
- Determine the sample size using an appropriate formula
- For quantitative: use Taro Yamane formula or Cochran formula — show the calculation with actual numbers
- For qualitative: justify purposive/snowball/theoretical sampling with reasoning
- Name the sampling technique and justify its choice
- State the final sample size clearly

3.6 INSTRUMENT FOR DATA COLLECTION
- Describe the primary instrument (questionnaire, interview guide, observation checklist)
- Describe the structure of the instrument (sections, number of items, scale used)
- For questionnaires: specify the Likert scale used (e.g. 5-point: Strongly Agree to Strongly Disagree)
- Justify why this instrument is appropriate for the research design

3.7 VALIDITY OF THE INSTRUMENT
- Explain how content validity was established (expert review, supervisor review)
- Explain face validity if applicable
- Mention construct validity for quantitative studies
- State that the instrument was reviewed by the supervisor and relevant experts

3.8 RELIABILITY OF THE INSTRUMENT
- For quantitative: specify Cronbach's Alpha threshold (0.7 or above is acceptable)
- State that a pilot study was conducted (specify sample size for pilot — typically 10–15% of main sample)
- State the Cronbach's Alpha coefficient obtained from the pilot
- For qualitative: discuss transferability, credibility, and dependability instead

3.9 METHOD OF DATA COLLECTION
- Describe how the questionnaires/instruments were administered
- State whether it was self-administered, online, or researcher-administered
- Describe how respondents were reached in the Nigerian context
- Mention any ethical considerations (anonymity, informed consent, voluntary participation)

3.10 METHOD OF DATA ANALYSIS
- State the statistical tools to be used for each research question/hypothesis
- For quantitative: specify tools like descriptive statistics (mean, frequency, percentage), inferential statistics (regression, correlation, chi-square, ANOVA, t-test) — match to the hypotheses
- For qualitative: specify thematic analysis, content analysis, or narrative analysis
- State the software to be used (SPSS version 23+, Microsoft Excel, or Atlas.ti for qualitative)
- Explain how hypotheses will be tested (significance level: p < 0.05)

3.11 ETHICAL CONSIDERATIONS
- Informed consent from respondents
- Confidentiality and anonymity
- Voluntary participation
- Data storage and privacy
- Institutional approval if applicable

WRITING REQUIREMENTS:
- Every methodological choice must be justified — not just described
- Cite methodology authors for key decisions (Creswell, 2014; Kothari, 2004; Saunders et al., 2019)
- The sampling calculation must show actual numbers — not just the formula
- Be specific about the Nigerian context throughout
- Minimum chapter length: 1,800 words

Write the full chapter now. Do not summarise or truncate any section."""


def _get_design_instructions(research_type: str, department: str) -> str:
    """Additional instructions based on research design and department."""
    dept_lower = department.lower()

    if research_type == "qualitative":
        return """QUALITATIVE DESIGN SPECIFIC INSTRUCTIONS:
- The instrument is an interview guide or focus group guide — not a questionnaire
- Sample size is smaller (10–30 participants) and justified by saturation
- Data analysis uses thematic analysis — describe the 6-step Braun & Clarke process
- Validity is discussed as trustworthiness (credibility, transferability, dependability, confirmability)
- No statistical hypothesis testing — use research propositions instead"""

    if research_type == "mixed":
        return """MIXED METHODS DESIGN SPECIFIC INSTRUCTIONS:
- Explain whether the design is sequential exploratory, sequential explanatory, or concurrent triangulation
- Describe both the quantitative and qualitative strands separately
- Explain how the two strands are integrated
- Justify why a mixed approach is superior to either alone for this study"""

    if any(d in dept_lower for d in ["account", "finance", "banking", "economics"]):
        return """ACCOUNTING/FINANCE SPECIFIC INSTRUCTIONS:
- Use ex-post facto or survey research design
- For studies using secondary data: describe data sources (CBN annual reports, NSE data, company annual reports)
- Specify panel data or time series analysis if applicable
- Hypotheses must be tested with regression analysis or correlation
- Specify OLS regression or Pearson correlation as appropriate"""

    if any(d in dept_lower for d in ["computer", "software", "engineering", "technology"]):
        return """ENGINEERING/CS SPECIFIC INSTRUCTIONS:
- Describe the system development methodology if applicable (Agile, Waterfall, SDLC)
- For experimental designs: describe the experimental setup and control variables
- For survey-based CS research: follow standard quantitative methodology
- If building a system: describe the development tools, programming languages, and testing methodology"""

    return ""


print("[chapter_3.py] Chapter 3 prompt builder loaded.")