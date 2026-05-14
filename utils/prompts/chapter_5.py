print("[chapter_5.py] Loading Chapter 5 prompt builder...")


def get_chapter_5_prompt(brief: dict) -> str:
    print(f"[chapter_5] Building prompt for: {brief.get('topic', '')[:60]}")

    topic             = brief.get("topic", "")
    research_question = brief.get("research_question", "")
    department        = brief.get("department", "")
    university        = brief.get("university", "")
    citation_style    = brief.get("citation_style", "apa7") or "apa7"
    research_type     = brief.get("research_type", "quantitative") or "quantitative"
    objectives        = brief.get("objectives", [])
    hypotheses        = brief.get("hypotheses", [])
    population        = brief.get("population", "")
    time_frame        = brief.get("time_frame", "")
    level             = brief.get("academic_level", "bsc") or "bsc"
    nigerian_ctx      = brief.get("nigerian_context", "")
    chapter_format    = brief.get("chapter_format", "")
    outline           = brief.get("chapter_5_outline", "")

    objectives_text = ""
    if objectives:
        objectives_text = "OBJECTIVES (every one must appear in summary of findings):\n"
        for i, obj in enumerate(objectives, 1):
            objectives_text += f"{i}. {obj}\n"

    hypotheses_text = ""
    if hypotheses:
        hypotheses_text = "HYPOTHESES TESTED IN CHAPTER 4:\n"
        for i, hyp in enumerate(hypotheses, 1):
            hypotheses_text += f"{i}. {hyp}\n"

    contrib_instruction = ""
    if level in ["msc", "mba", "mpa", "mphil", "phd"]:
        contrib_instruction = """
5.5 CONTRIBUTIONS TO KNOWLEDGE (REQUIRED for postgraduate)
- State 3-5 specific original contributions to:
  * Theoretical body of knowledge
  * Empirical body of knowledge (new evidence from Nigerian context)
  * Policy and practice
- Must be specific — not generic statements
- Example: "This study is the first to empirically examine X in Y in Nigeria using Z method"
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

    return f"""Write a complete, publication-quality Chapter 5 (Summary, Conclusion and Recommendations) for this final year project.
{outline_injection}
{format_injection}
TOPIC: {topic}
RESEARCH QUESTION: {research_question}
DEPARTMENT: {department}
UNIVERSITY: {university}
CITATION STYLE: {citation_style.upper()}
LEVEL: {level.upper()}
SCOPE: {population} | {time_frame}
NIGERIAN CONTEXT: {nigerian_ctx}

{objectives_text}
{hypotheses_text}

STANDARD CHAPTER 5 SECTIONS (use if no outline provided above):

5.1 INTRODUCTION
- Brief paragraph re-introducing the chapter
- State the purpose of the study in one sentence
- Overview of what this chapter contains

5.2 SUMMARY OF FINDINGS
- NOT a summary of the whole project — a summary of what was FOUND
- Address each research objective one by one in dedicated paragraphs
- For each: state the objective, what was found, statistical outcome if applicable
- For each hypothesis: state whether accepted or rejected and the implication
- Use specific figures and outcomes from Chapter 4
- Minimum 500 words
- Label as 5.2.1 Finding Related to Objective One, 5.2.2 etc.

5.3 CONCLUSION
- Draw overall conclusions from all findings
- Answer the main research question directly and definitively
- Relate to the theoretical framework from Chapter 2
- Discuss what findings mean for the Nigerian context specifically
- Do NOT introduce new information
- Must connect back to the Statement of the Problem from Chapter 1
- Minimum 300 words

5.4 RECOMMENDATIONS
- 5-7 specific, actionable recommendations
- Each must:
  * Be derived from a specific finding
  * Be addressed to a specific stakeholder
  * Be realistic within Nigerian context
  * Be specific enough to implement
- Include at least 2 directed at Nigerian policy/government
- Include 1 directed at academic/research community

{contrib_instruction}

5.6 SUGGESTIONS FOR FURTHER STUDIES
- 3-4 specific areas for future research
- Each addresses a limitation of this study
- Proposes a specific direction with explanation of value

WRITING REQUIREMENTS:
- Must feel like a confident authoritative conclusion — not a repetition
- Every finding must connect to something specific from Chapter 4
- Recommendations must reflect deep understanding of Nigerian context
- The conclusion must answer: "So what? What does this mean for Nigeria?"
- Minimum 1,500 words

FINAL INSTRUCTION:
After the chapter output this marker exactly:
<!--PROJECT_COMPLETE-->

Write the full chapter now. Do not summarise or truncate any section."""


print("[chapter_5.py] Chapter 5 prompt builder loaded.")