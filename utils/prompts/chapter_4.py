print("[chapter_4.py] Loading Chapter 4 prompt builder...")


def get_chapter_4_prompt(brief: dict, previous_chapters: dict) -> str:
    print(f"[chapter_4] Building prompt for: {brief.get('topic', '')[:60]}")

    topic          = brief.get("topic", "")
    research_type  = brief.get("research_type", "quantitative") or "quantitative"
    department     = brief.get("department", "") or ""
    university     = brief.get("university", "")
    citation_style = brief.get("citation_style", "apa7") or "apa7"
    objectives     = brief.get("objectives", [])
    hypotheses     = brief.get("hypotheses", [])
    student_data   = brief.get("student_data", "")
    population     = brief.get("population", "")
    time_frame     = brief.get("time_frame", "2024")
    chapter_format = brief.get("chapter_format", "")
    outline        = brief.get("chapter_4_outline", "")

    objectives_text = ""
    if objectives:
        objectives_text = "OBJECTIVES (each must be addressed in findings):\n"
        for i, obj in enumerate(objectives, 1):
            objectives_text += f"{i}. {obj}\n"

    hypotheses_text = ""
    if hypotheses:
        hypotheses_text = "HYPOTHESES TO TEST:\n"
        for i, hyp in enumerate(hypotheses, 1):
            hypotheses_text += f"{i}. {hyp}\n"

    ch3_excerpt = ""
    if previous_chapters.get(3):
        content     = previous_chapters[3]
        ch3_excerpt = content[:600] + "..." if len(content) > 600 else content

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

    data_instructions = _get_data_analysis_instructions(research_type, department, student_data)

    return f"""Write a complete, publication-quality Chapter 4 (Data Presentation, Analysis and Discussion of Findings) for this final year project.
{outline_injection}
{format_injection}
TOPIC: {topic}
RESEARCH DESIGN: {research_type.upper()}
POPULATION/SCOPE: {population}
DEPARTMENT: {department}
UNIVERSITY: {university}
CITATION STYLE: {citation_style.upper()}

{objectives_text}
{hypotheses_text}

STUDENT'S DATA:
{student_data if student_data else "No data provided — write structure only, mark every table and calculation with [INSERT DATA HERE]"}

METHODOLOGY FROM CHAPTER 3 (for consistency):
{ch3_excerpt}

{data_instructions}

STANDARD CHAPTER 4 SECTIONS (use if no outline provided above):

4.1 INTRODUCTION
- Brief paragraph introducing the chapter
- State the response rate achieved
- State number of questionnaires distributed vs returned vs valid
- State data was analysed using tools from Chapter 3

4.2 DEMOGRAPHIC DATA OF RESPONDENTS
- Present demographic profile (Section A of questionnaire)
- Use tables with frequency counts and percentages
- Comment briefly on each demographic table

4.3 PRESENTATION AND ANALYSIS OF DATA
- Address each research question/objective with a dedicated subsection (4.3.1, 4.3.2 etc.)
- For each: state the question, present data in labelled table, calculate means and SDs,
  interpret using decision rule, write 2-3 paragraphs of analysis

4.4 TEST OF HYPOTHESES
- Test each hypothesis from Chapter 1
- For each: state H0 and H1, state the statistical test used, present results in table,
  state decision rule (reject H0 if p < 0.05), state decision and meaning

4.5 DISCUSSION OF FINDINGS
- Synthesise key findings across all research questions
- Compare with literature reviewed in Chapter 2
- For each major finding relate to a specific study
- Discuss Nigerian-specific implications
- Minimum 500 words

TABLE FORMAT:
Table 4.1: Title
| Variable | Frequency | Percentage (%) |
|----------|-----------|----------------|
| Category | 120       | 60.0           |
| Total    | 200       | 100.0          |
Source: Field Survey, {time_frame}

DATA HANDLING RULES:
- If student provided data: use EXACTLY their numbers
- If no data: write structure only, mark every calculation with [INSERT DATA HERE]
- NEVER fabricate data values, percentages, or statistical results

Write the full chapter now. Do not summarise or truncate any section."""


def _get_data_analysis_instructions(
    research_type: str,
    department: str,
    student_data: str,
) -> str:
    dept_lower    = (department or "").lower()
    research_type = (research_type or "quantitative").lower()

    if research_type == "qualitative":
        return """QUALITATIVE ANALYSIS INSTRUCTIONS:
- Use thematic analysis to present findings
- Organise by themes that emerge from the data
- Use direct quotes from transcripts to support themes
- Format: "Quote here" (Respondent 3, Male, 32 years, Lagos)
- Identify patterns, contradictions, and unexpected findings
- No statistical tables — narrative presentation"""

    if any(d in dept_lower for d in ["account", "finance", "banking", "economics"]):
        return """ACCOUNTING/FINANCE ANALYSIS INSTRUCTIONS:
- Descriptive statistics table first (mean, std dev, min, max for all variables)
- Correlation analysis — Pearson/Spearman correlation matrix
- Regression analysis — coefficients, t-statistics, p-values, R², Adjusted R², F-statistic
- Test hypotheses using regression coefficients (p < 0.05)
- Interpret economic significance not just statistical significance
- Reference Nigerian financial data (CBN, SEC, NSE)"""

    return """QUANTITATIVE ANALYSIS INSTRUCTIONS:
- Use 5-point Likert scale interpretation:
  4.50-5.00 = Strongly Agree, 3.50-4.49 = Agree, 2.50-3.49 = Undecided,
  1.50-2.49 = Disagree, 1.00-1.49 = Strongly Disagree
- Present frequency tables, mean scores, and standard deviations
- Use chi-square, t-test, or ANOVA for hypothesis testing as specified in Chapter 3
- Calculate degrees of freedom and compare to critical value"""


print("[chapter_4.py] Chapter 4 prompt builder loaded.")