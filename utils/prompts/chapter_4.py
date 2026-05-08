print("[chapter_4.py] Loading Chapter 4 prompt builder...")


def get_chapter_4_prompt(brief: dict, previous_chapters: dict) -> str:
    """
    Build the user-turn prompt for Chapter 4: Data Presentation and Analysis.
    This chapter requires the student's actual data.
    If data is provided, Claude analyses it.
    If not, the bot refuses to generate and offers alternatives.

    The student_data field in brief is set by the chapters handler
    after the data gate is passed.
    """
    print(f"[chapter_4] Building prompt for: {brief.get('topic', '')[:60]}")

    topic          = brief.get("topic", "")
    research_type  = brief.get("research_type", "quantitative")
    department     = brief.get("department", "")
    university     = brief.get("university", "")
    citation_style = brief.get("citation_style", "apa7")
    objectives     = brief.get("objectives", [])
    hypotheses     = brief.get("hypotheses", [])
    student_data   = brief.get("student_data", "")
    population     = brief.get("population", "")

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

    # Extract chapter 3 methodology for consistency
    ch3_excerpt = ""
    if previous_chapters.get(3):
        ch3_content = previous_chapters[3]
        ch3_excerpt = ch3_content[:600] + "..." if len(ch3_content) > 600 else ch3_content

    data_instructions = _get_data_analysis_instructions(research_type, department, student_data)

    return f"""Write a complete, publication-quality Chapter 4 (Data Presentation, Analysis and Discussion of Findings) for this final year project:

TOPIC: {topic}
RESEARCH DESIGN: {research_type.upper()}
POPULATION/SCOPE: {population}
DEPARTMENT: {department}
UNIVERSITY: {university}
CITATION STYLE: {citation_style.upper()}

{objectives_text}
{hypotheses_text}

STUDENT'S DATA:
{student_data if student_data else "No data provided — see instructions below"}

METHODOLOGY FROM CHAPTER 3 (for consistency):
{ch3_excerpt}

{data_instructions}

CHAPTER 4 MUST CONTAIN ALL OF THESE SECTIONS IN ORDER:

4.1 INTRODUCTION
- Brief paragraph introducing the chapter
- State the response rate achieved
- For quantitative: state the number of questionnaires distributed vs returned vs valid
- State that data was analysed using [tools from Chapter 3]

4.2 DEMOGRAPHIC DATA OF RESPONDENTS
- Present the demographic profile of respondents (Section A of questionnaire)
- Use tables with frequency counts and percentages
- Include: gender, age group, educational qualification, years of experience (or other relevant demographics)
- Comment briefly on each demographic table

4.3 PRESENTATION AND ANALYSIS OF DATA
- Address each research question/objective with a dedicated subsection (4.3.1, 4.3.2, etc.)
- For each subsection:
  * State the research question being addressed
  * Present the data in a clearly labelled table
  * Calculate mean scores and standard deviations where applicable
  * Interpret the mean scores using the decision rule (e.g. mean ≥ 3.0 = accepted)
  * Write 2–3 paragraphs of analysis and interpretation

4.4 TEST OF HYPOTHESES
- Test each hypothesis stated in Chapter 1
- For each hypothesis:
  * State the null hypothesis (H₀) and alternate hypothesis (H₁)
  * State the statistical test used (from Chapter 3 methodology)
  * Present the results in a table (test statistic, df, p-value, decision)
  * State the decision rule (reject H₀ if p < 0.05)
  * State whether H₀ is rejected or not rejected and what that means

4.5 DISCUSSION OF FINDINGS
- Synthesise the key findings across all research questions
- Compare findings with the literature reviewed in Chapter 2
- For each major finding: relate it to a specific study from the literature review
- Explain agreements: "This finding aligns with Adeyemi (2020) who found..."
- Explain disagreements: "This contradicts Okafor (2022) who argued... This may be because..."
- Discuss Nigerian-specific implications of the findings
- Minimum 500 words

FORMATTING REQUIREMENTS FOR TABLES:
Since this is a text-based output, format tables as follows:
Table 4.1: Title of Table
| Variable | Frequency | Percentage (%) |
|----------|-----------|----------------|
| Male     | 120       | 60.0           |
| Female   | 80        | 40.0           |
| Total    | 200       | 100.0          |
Source: Field Survey, {brief.get('time_frame', '2024')}

IMPORTANT DATA HANDLING RULES:
- If student provided actual data: use EXACTLY their numbers — do not round differently or alter figures
- If student provided partial data: work with what is given and note what is missing
- Never fabricate specific data values, percentages, or statistical results
- If no data was provided: write the structure and framework only, clearly marking [INSERT DATA HERE] at every table and calculation

Write the full chapter now. Do not summarise or truncate any section."""


def _get_data_analysis_instructions(
    research_type: str,
    department: str,
    student_data: str,
) -> str:
    """Return design and department-specific data analysis instructions."""
    dept_lower = department.lower()

    if research_type == "qualitative":
        return """QUALITATIVE ANALYSIS INSTRUCTIONS:
- Use thematic analysis to present findings
- Organise by themes that emerge from the data (not by research questions)
- Use direct quotes from interview transcripts to support themes
- Format quotes as: "Quote here" (Respondent 3, Male, 32 years, Lagos)
- Identify patterns, contradictions, and unexpected findings
- No statistical tables — use narrative presentation"""

    if any(d in dept_lower for d in ["account", "finance", "banking", "economics"]):
        return """ACCOUNTING/FINANCE ANALYSIS INSTRUCTIONS:
- Use descriptive statistics table first (mean, std dev, min, max for all variables)
- Run correlation analysis — present Pearson/Spearman correlation matrix
- Run regression analysis — present: coefficients, t-statistics, p-values, R², Adjusted R², F-statistic
- Test hypotheses using regression coefficients (p < 0.05 threshold)
- Interpret economic significance, not just statistical significance
- Reference Nigerian financial data where used (CBN, SEC, NSE)"""

    # Standard quantitative
    return """QUANTITATIVE ANALYSIS INSTRUCTIONS:
- Use 4-point or 5-point Likert scale mean interpretation table
- Decision rule for 5-point scale: 4.50–5.00 = Strongly Agree, 3.50–4.49 = Agree, 2.50–3.49 = Undecided, 1.50–2.49 = Disagree, 1.00–1.49 = Strongly Disagree
- Present frequency tables, mean scores, and standard deviations
- Use chi-square or t-test or ANOVA for hypothesis testing as specified in Chapter 3
- Calculate degrees of freedom and compare test statistic to critical value"""


print("[chapter_4.py] Chapter 4 prompt builder loaded.")