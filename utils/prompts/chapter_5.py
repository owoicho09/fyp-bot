print("[chapter_5.py] Loading Chapter 5 prompt builder...")


def get_chapter_5_prompt(brief: dict) -> str:
    """
    Build the user-turn prompt for Chapter 5: Summary, Conclusion and Recommendations.
    This chapter must tie together everything from Chapters 1–4.
    It is the student's final word — it must be substantive, not generic.
    """
    print(f"[chapter_5] Building prompt for: {brief.get('topic', '')[:60]}")

    topic          = brief.get("topic", "")
    research_question = brief.get("research_question", "")
    department     = brief.get("department", "")
    university     = brief.get("university", "")
    citation_style = brief.get("citation_style", "apa7")
    research_type  = brief.get("research_type", "quantitative")
    objectives     = brief.get("objectives", [])
    hypotheses     = brief.get("hypotheses", [])
    population     = brief.get("population", "")
    time_frame     = brief.get("time_frame", "")
    level          = brief.get("academic_level", "bsc")
    nigerian_ctx   = brief.get("nigerian_context", "")

    objectives_text = ""
    if objectives:
        objectives_text = "OBJECTIVES FROM CHAPTER 1 (every objective must appear in the summary of findings):\n"
        for i, obj in enumerate(objectives, 1):
            objectives_text += f"{i}. {obj}\n"

    hypotheses_text = ""
    if hypotheses:
        hypotheses_text = "HYPOTHESES TESTED IN CHAPTER 4:\n"
        for i, hyp in enumerate(hypotheses, 1):
            hypotheses_text += f"{i}. {hyp}\n"

    # Postgrad requires contributions to knowledge section
    contrib_instruction = ""
    if level in ["msc", "mba", "mpa", "mphil", "phd"]:
        contrib_instruction = """
5.5 CONTRIBUTIONS TO KNOWLEDGE
- This section is REQUIRED for postgraduate projects
- State 3–5 specific, original contributions this study makes to:
  * The theoretical body of knowledge (new application of existing theory)
  * The empirical body of knowledge (new evidence from Nigerian context)
  * Policy and practice (actionable insights for practitioners/policymakers)
- Contributions must be specific — not generic statements like "This study adds to knowledge"
- Example: "This study is the first to empirically examine X in the context of Y in Nigeria using Z method"
"""

    return f"""Write a complete, publication-quality Chapter 5 (Summary, Conclusion and Recommendations) for this final year project:

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

CHAPTER 5 MUST CONTAIN ALL OF THESE SECTIONS IN ORDER:

5.1 INTRODUCTION
- Brief paragraph re-introducing the chapter
- State the purpose of the study in one sentence
- Give a brief overview of what this chapter contains

5.2 SUMMARY OF FINDINGS
- This is NOT a summary of the whole project — it is a summary of what was FOUND
- Address each research objective one by one in dedicated paragraphs
- For each objective: state the objective, state what was found, state the statistical outcome if applicable
- For each hypothesis: state whether it was accepted or rejected and the implication
- Use transitional phrases to flow between findings
- Be specific — use actual figures and outcomes from Chapter 4
- Minimum 500 words
- Label subsections as: 5.2.1 Finding Related to Objective One, 5.2.2 etc.

5.3 CONCLUSION
- Draw overall conclusions from the sum of all findings
- Answer the main research question directly and definitively
- Relate conclusions to the theoretical framework from Chapter 2
- Discuss what the findings mean for the Nigerian context specifically
- Do NOT introduce new information in the conclusion
- Must connect directly back to the Statement of the Problem from Chapter 1
- Minimum 300 words

5.4 RECOMMENDATIONS
- Provide 5–7 specific, actionable recommendations
- Each recommendation must:
  * Be directly derived from a specific finding (not generic advice)
  * Be addressed to a specific stakeholder (government, regulators, organisations, practitioners, educators)
  * Be realistic within the Nigerian context
  * Be specific enough to be implemented — not vague suggestions
- Format as numbered list with 2–3 sentences of explanation per recommendation
- Include at least 2 recommendations directed at Nigerian policy/government bodies
- Include 1 recommendation directed at academic/research community

{contrib_instruction}

5.6 SUGGESTIONS FOR FURTHER STUDIES
- Suggest 3–4 specific areas for future research
- Each suggestion should:
  * Address a limitation of this study
  * Propose a specific direction (different methodology, broader population, different Nigerian context)
  * Explain why this future research would be valuable
- This section shows intellectual humility and opens dialogue with future researchers

WRITING REQUIREMENTS:
- Chapter 5 must feel like a confident, authoritative conclusion — not a repetition
- Every finding summarised must connect to something specific from Chapter 4
- Recommendations must feel like they came from someone who deeply understands the Nigerian context
- Avoid generic academic filler — every sentence must add value
- The conclusion must answer: "So what? What does this mean for Nigeria?"
- Minimum chapter length: 1,500 words

FINAL INSTRUCTION:
After the chapter, output this marker so the system knows the full project is complete:
<!--PROJECT_COMPLETE-->

Write the full chapter now. Do not summarise or truncate any section."""


print("[chapter_5.py] Chapter 5 prompt builder loaded.")