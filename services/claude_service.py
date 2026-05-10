print("[claude_service.py] Loading Claude service...")

import json
import re
import asyncio
from anthropic import AsyncAnthropic
from config import (
    ANTHROPIC_API_KEY,
    MODEL_INTAKE,
    MODEL_CHAPTER_2,
    MODEL_DEFAULT,
)

client = AsyncAnthropic(
    api_key=ANTHROPIC_API_KEY,
    timeout=120.0,
)
print("[claude_service.py] Anthropic async client ready.")


# ─── WRITING BENCHMARK ────────────────────────────────────────────────────────
# Extracted from an accepted Nigerian university final year project.
# This is style guidance only — never copy content from this.
# Use it to calibrate sentence variety, paragraph structure, academic tone,
# and Nigerian grounding that supervisors actually accept.

NIGERIAN_ACADEMIC_WRITING_BENCHMARK = """
WRITING STYLE BENCHMARK (extracted from an accepted Nigerian university project):

SENTENCE VARIETY:
- Mix short sentences (8-12 words) with long complex ones (25-35 words)
- Never write three sentences of similar length consecutively
- Example of good variety: "Radiometric surveys measure natural radioactivity. The three 
  principal radioelements — potassium, uranium, and thorium — emit gamma rays whose 
  distribution patterns directly correlate with specific rock types, mineralisation styles, 
  and structural features that have evolved over millions of years of tectonic activity."

PARAGRAPH STRUCTURE:
- 4-6 sentences per paragraph
- Every paragraph must open with a different word from the previous paragraph
- Open with: "The...", "This study...", "In...", "By...", "Unlike...", "Recent...", 
  "Among...", "Several...", "Such...", "These..." — rotate naturally
- Close every section with a transitional sentence to the next section

PRECISION AND SPECIFICITY:
- Always use exact values when discussing data: "0.1% to over 3.1%", not "varying concentrations"
- Always name specific Nigerian locations: towns, LGAs, states, coordinates
- Always name specific institutions: NGSA, CBN, NBS, FMOH — never say "government agencies"
- Cite specific years for all statistics and policies

SYNTHESIS IN LITERATURE REVIEW:
- Never list studies one after another
- Always synthesise: "While Author A found X, Author B demonstrated Y, and Author C 
  challenged both by showing Z, the collective evidence suggests..."
- Identify contradictions, gaps, and agreements between studies
- Always end literature sections with what gap the current study fills

HEDGING LANGUAGE (mandatory for empirical claims):
- Use: "suggests", "indicates", "likely reflects", "may represent", "appears to be"
- Only use definitive language when citing confirmed data
- Wrong: "This area has gold deposits"
- Right: "Radiometric anomalies in this area suggest the presence of potential gold mineralisation"

NIGERIAN GROUNDING (must appear naturally, not forced):
- Name specific Nigerian states, LGAs, towns in the study area
- Reference Nigerian institutional data sources naturally in context
- Mention Nigerian policy context where relevant (solid minerals policy, NUC requirements)
- Reference Nigerian researchers alongside international ones in literature review

WHAT SUPERVISORS REJECT:
- "It is important to note that..." — delete this phrase entirely
- "It is worth mentioning..." — delete
- "Furthermore," starting every paragraph — vary with: "Similarly,", "In contrast,", 
  "Building on this,", "This finding aligns with,", "Conversely,"
- Generic opening paragraphs that could apply to any country or topic
- Conclusions that do not directly answer the research questions
- Recommendations not derived from specific findings

SECTION TRANSITIONS (required):
- Every major section must end with 1-2 sentences bridging to the next section
- Example: "Having established the structural framework of the study area, the following 
  section reviews the geophysical literature that underpins the methodological approach 
  adopted in this research."
"""


# ─── JSON PARSING UTILITY ─────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """
    Robustly extract a JSON object from a Claude response.
    Handles: clean JSON, JSON in markdown fences, JSON with text before/after.
    Never raises — always returns a dict.
    """
    if not raw:
        return {}
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass
    try:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group(0))
    except json.JSONDecodeError:
        pass
    print(f"[claude] _extract_json: all attempts failed. Raw: {raw[:200]}")
    return {}


def _safe_reply(raw: str, parsed: dict) -> str:
    """
    Extract reply from parsed JSON.
    If parsing failed, strip any JSON block from raw before returning.
    Never returns raw JSON to the student.
    """
    reply = parsed.get("reply", "")
    if reply:
        return reply
    clean = re.sub(r"\{[\s\S]*\}", "", raw).strip()
    return clean if clean else "Could you say that again?"


# ─── INTAKE AGENT ─────────────────────────────────────────────────────────────

async def run_intake_agent(
    conversation_history: list[dict],
    student_context: dict,
) -> dict:
    """
    Drive the research brief extraction conversation.
    Returns extracted fields and whether the brief is complete.
    """
    print(f"[claude] run_intake_agent: {len(conversation_history)} turns")
    system_prompt = _build_intake_system_prompt(student_context)
    try:
        response = await client.messages.create(
            model=MODEL_INTAKE,
            max_tokens=1024,
            system=system_prompt,
            messages=conversation_history,
        )
        raw    = response.content[0].text.strip()
        parsed = _extract_json(raw)
        print(f"[claude] Intake extracted: {list(parsed.get('extracted', {}).keys())}")
        print(f"[claude] Brief complete: {parsed.get('brief_complete', False)}")
        return {
            "reply":          parsed.get("reply") or _safe_reply(raw, parsed) or "Tell me more about your project.",
            "extracted":      parsed.get("extracted", {}),
            "brief_complete": parsed.get("brief_complete", False),
        }
    except Exception as e:
        print(f"[claude] run_intake_agent ERROR: {e}")
        return {
            "reply":          "I had a moment — could you tell me about your project again?",
            "extracted":      {},
            "brief_complete": False,
        }


def _build_intake_system_prompt(ctx: dict) -> str:
    already_known = []
    if ctx.get("academic_level"): already_known.append(f"Academic level: {ctx['academic_level']}")
    if ctx.get("faculty"):        already_known.append(f"Faculty: {ctx['faculty']}")
    if ctx.get("department"):     already_known.append(f"Department: {ctx['department']}")
    if ctx.get("university"):     already_known.append(f"University: {ctx['university']}")
    if ctx.get("topic"):          already_known.append(f"Topic so far: {ctx['topic']}")
    known_text = "\n".join(already_known) if already_known else "Nothing collected yet."

    return f"""You are the intake agent for FYP Mentor, helping Nigerian university 
final year students set up their research project brief.

WHAT YOU ALREADY KNOW:
{known_text}

YOUR JOB:
Extract a complete research brief from the student's message.
You get ONE follow-up question maximum — make it count.

WHAT TO EXTRACT:
- topic: their exact research topic — never rephrase or change it
- research_question: what they are specifically trying to find out
- population: who/what they are studying, which Nigerian state/city/institution
- time_frame: e.g. 2019–2024
- research_type: quantitative/qualitative/mixed — infer from topic and department
- citation_style: infer from department (engineering=ieee, medicine=vancouver, 
  law=oscola, sciences/social=apa7, humanities=mla) — only ask if genuinely unclear
- nigerian_context: specific Nigerian places, institutions, policies they mention
- student_background: what they already know or believe about this topic
- chapter_format: if they mention their school's specific chapter headings or 
  section names, extract them exactly

CRITICAL RULES:
1. NEVER suggest a different topic. Accept whatever topic they give.
2. NEVER ask about citation style or research design — infer from department and topic.
3. Set brief_complete to true if you have: topic + at least 2 of 
   (research_question, population, time_frame, research_type).
4. Your ONE follow-up: ask about the single most important missing piece —
   usually population/scope or time frame if missing.
5. Keep your reply warm and concise — 1 to 2 sentences only.
6. If they mention their school uses specific chapter headings or section names,
   note that in chapter_format — this is valuable for accurate generation.

RESPONSE FORMAT — always respond in this exact JSON, nothing outside it:
{{
  "reply": "Your brief warm message to the student",
  "extracted": {{
    "topic": "their exact topic — omit if not identified",
    "research_question": "omit if not identified",
    "population": "omit if not identified",
    "time_frame": "omit if not identified",
    "research_type": "quantitative|qualitative|mixed — omit if cannot infer",
    "citation_style": "apa7|harvard|ieee|vancouver|oscola|chicago|mla — omit if cannot infer",
    "nigerian_context": "omit if not mentioned",
    "student_background": "omit if not mentioned",
    "chapter_format": "omit if not mentioned"
  }},
  "brief_complete": false
}}

Set brief_complete to true as soon as you have enough. Never fish for more."""


# ─── TOPIC VALIDATION ─────────────────────────────────────────────────────────

async def validate_topic_with_ai(
    topic: str,
    department: str,
    level: str,
    university: str,
) -> dict:
    print(f"[claude] validate_topic_with_ai: '{topic[:60]}'")
    prompt = f"""A Nigerian university student proposes this final year project topic:
"{topic}"

Context: Department={department}, Level={level}, University={university}

Evaluate only: is this researchable as a final year project in Nigeria?
Accept broad topics — students refine them with their supervisor.
Only reject if completely unresearchable or nonsensical.

Respond ONLY in this exact JSON:
{{
  "is_valid": true or false,
  "feedback": "one sentence of specific constructive feedback",
  "suggestions": ["refined version 1", "refined version 2", "alternative topic"]
}}

If is_valid is true, suggestions can be empty list.
Default to is_valid: true unless clearly unresearchable."""

    try:
        response = await client.messages.create(
            model=MODEL_INTAKE,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw    = response.content[0].text.strip()
        parsed = _extract_json(raw)
        print(f"[claude] Topic valid: {parsed.get('is_valid')}")
        return parsed if parsed else {"is_valid": True, "feedback": "Topic accepted.", "suggestions": []}
    except Exception as e:
        print(f"[claude] validate_topic_with_ai ERROR: {e}")
        return {"is_valid": True, "feedback": "Topic accepted.", "suggestions": []}


# ─── RESEARCH DESIGN RECOMMENDATION ──────────────────────────────────────────

async def recommend_research_design(
    topic: str,
    department: str,
    research_question: str,
) -> str:
    print(f"[claude] recommend_research_design: '{topic[:60]}'")
    prompt = f"""Nigerian final year student needs research design guidance.
Topic: {topic}
Department: {department}
Research question: {research_question}

Recommend quantitative, qualitative, or mixed methods.
2-3 sentences: why this design suits their topic, and what data collection method.
Be practical and specific to Nigerian university context."""

    try:
        response = await client.messages.create(
            model=MODEL_INTAKE,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[claude] recommend_research_design ERROR: {e}")
        return "Quantitative research design using a structured questionnaire is recommended."


# ─── CHAPTER GENERATION ───────────────────────────────────────────────────────

async def generate_chapter(
    chapter_number: int,
    brief: dict,
    citations: list[dict] = None,
    live_stats: dict = None,
    previous_chapters: dict = None,
) -> str:
    print(f"[claude] generate_chapter: chapter={chapter_number}")
    model = MODEL_CHAPTER_2 if chapter_number == 2 else MODEL_DEFAULT
    print(f"[claude] Using model: {model}")

    system_prompt  = _build_chapter_system_prompt(brief, live_stats, previous_chapters)
    chapter_prompt = _build_chapter_user_prompt(chapter_number, brief, citations, previous_chapters)

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": chapter_prompt}],
        )
        content = response.content[0].text.strip()
        print(f"[claude] Chapter {chapter_number} generated. Length: {len(content)}")
        return content
    except Exception as e:
        print(f"[claude] generate_chapter ERROR: {e}")
        raise


def _build_chapter_system_prompt(
    brief: dict,
    live_stats: dict = None,
    previous_chapters: dict = None,
) -> str:
    from utils.helpers import summarise_brief_for_prompt
    from services.search_service import format_stats_for_prompt

    brief_text = summarise_brief_for_prompt(brief)
    stats_text = format_stats_for_prompt(live_stats or {})

    prev_text = ""
    if previous_chapters:
        prev_text = "\n\nPREVIOUSLY GENERATED CHAPTERS (maintain consistency):\n"
        for ch_num, ch_content in previous_chapters.items():
            preview = ch_content[:1000] + "\n[...continues...]" if len(ch_content) > 1000 else ch_content
            prev_text += f"\n--- Chapter {ch_num} excerpt ---\n{preview}\n"

    # Turnitin-aware instructions
    turnitin_rules = ""
    if brief.get("turnitin"):
        turnitin_rules = """
TURNITIN-AWARE WRITING (student confirmed Turnitin is used):
- Vary sentence length aggressively — short (8-12 words) alternating with long complex (25-35 words)
- Never start consecutive paragraphs with the same word
- Use first-person framing where appropriate: "This study...", "The researcher..."
- Use active voice at least 40% of the time
- Weave in Nigerian-specific examples, institutions, and place names naturally
- These patterns are the strongest signals that a real Nigerian student wrote this
"""

    # Department-specific rules
    dept_lower  = (brief.get("department") or "").lower()
    faculty     = (brief.get("faculty") or "").lower()
    dept_rules  = _get_department_rules(dept_lower, faculty)

    # Level-appropriate writing standard
    level_rules = _get_level_rules(brief.get("academic_level", "bsc"))

    # Citation style rules
    citation_rules = _get_citation_rules(brief.get("citation_style", "apa7"))

    # Custom chapter format from student's university
    chapter_format_note = ""
    if brief.get("chapter_format"):
        chapter_format_note = f"""
STUDENT'S UNIVERSITY CHAPTER FORMAT:
The student's university uses these specific section headings:
{brief['chapter_format']}
Use these exact headings in the appropriate chapters instead of generic ones.
"""

    return f"""You are an expert Nigerian academic research writer calibrated to write 
exactly as Nigerian university supervisors expect and accept.

{brief_text}

{stats_text}
{prev_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WRITING STYLE BENCHMARK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{NIGERIAN_ACADEMIC_WRITING_BENCHMARK}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE RULES — NEVER VIOLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. NEVER invent a citation — only cite papers from the provided list
2. NEVER fabricate data, statistics, or research findings
3. ALWAYS include specific Nigerian context — towns, LGAs, institutions, policies
4. ALWAYS maintain full consistency with Chapter 1 objectives and hypotheses
5. ALWAYS use citation style: {brief.get('citation_style', 'apa7').upper()}
6. ALWAYS write at appropriate level for {brief.get('university', 'a Nigerian university')}
7. For Law projects: NEVER fabricate case law or statutes
8. For Medicine/Health: NEVER make clinical recommendations
9. For Engineering: NEVER fabricate experimental data or measurements
10. NEVER truncate or summarise — write every section completely

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEVEL & WRITING STANDARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{level_rules}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPARTMENT-SPECIFIC RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{dept_rules}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CITATION FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{citation_rules}
{chapter_format_note}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Use numbered headings (1.1, 1.2, 2.1 etc.)
- Minimum 4 paragraphs per major section
- End every section with a transition sentence to the next
- End every chapter with a transitional paragraph to the next chapter
- Tables formatted in plain text with source lines
{turnitin_rules}"""


def _build_chapter_user_prompt(
    chapter_number: int,
    brief: dict,
    citations: list[dict] = None,
    previous_chapters: dict = None,
) -> str:
    print(f"[claude] _build_chapter_user_prompt: chapter={chapter_number}")
    from utils.prompts.chapter_1 import get_chapter_1_prompt
    from utils.prompts.chapter_2 import get_chapter_2_prompt
    from utils.prompts.chapter_3 import get_chapter_3_prompt
    from utils.prompts.chapter_4 import get_chapter_4_prompt
    from utils.prompts.chapter_5 import get_chapter_5_prompt

    builders = {
        1: get_chapter_1_prompt,
        2: get_chapter_2_prompt,
        3: get_chapter_3_prompt,
        4: get_chapter_4_prompt,
        5: get_chapter_5_prompt,
    }
    builder = builders.get(chapter_number)
    if not builder:
        raise ValueError(f"No prompt builder for chapter {chapter_number}")

    if chapter_number == 2:
        return builder(brief, citations or [])
    elif chapter_number == 4:
        return builder(brief, previous_chapters or {})
    else:
        return builder(brief)


# ─── SUPPORT FUNCTIONS ────────────────────────────────────────────────────────

def _get_level_rules(level: str) -> str:
    return {
        "bsc":   "Undergraduate (BSc/BA): Clear structure, well-supported arguments. "
                 "Show understanding and application — not just description. "
                 "Avoid oversimplification but do not over-complicate.",
        "hnd":   "HND: Practical applied focus. Strong industry/sector relevance. "
                 "Evidence-based arguments. Emphasise real-world application.",
        "pgd":   "PGD: More analytical than undergraduate. Critical engagement with theory. "
                 "Synthesise multiple sources.",
        "msc":   "MSc/MA: Sophisticated theoretical grounding. Original interpretation of literature. "
                 "Demonstrate mastery. Must include Contributions to Knowledge in Chapter 5.",
        "mba":   "MBA: Strong managerial and strategic implications. Connect theory to Nigerian "
                 "business practice. Evidence-based recommendations. "
                 "Must include Contributions to Knowledge in Chapter 5.",
        "mpa":   "MPA: Public policy and governance focus. Connect findings to Nigerian public "
                 "administration challenges. Recommendations directed at government. "
                 "Must include Contributions to Knowledge in Chapter 5.",
        "phd":   "PhD: Original contribution to knowledge is paramount. Deep critical engagement "
                 "with theory. Rigorous methodology. Independent scholarly voice. "
                 "Substantial Contributions to Knowledge section required.",
        "noun":  "NOUN: Clear structured academic writing. Practical Nigerian examples. "
                 "Follow NOUN project guidelines.",
    }.get(level, "Undergraduate level — clear, structured, evidence-based writing.")


def _get_citation_rules(style: str) -> str:
    rules = {
        "apa7": (
            "APA 7th Edition.\n"
            "In-text: (Author, Year) or Author (Year) found that...\n"
            "3+ authors: (Author et al., Year)\n"
            "Reference list: alphabetical, hanging indent\n"
            "Journal: Author, A. A. (Year). Title. Journal Name, Vol(Issue), pages. "
            "https://doi.org/xxx\n"
            "Heading: References"
        ),
        "harvard": (
            "Harvard Referencing.\n"
            "In-text: (Author, Year) or Author (Year) argues...\n"
            "Reference list: alphabetical, hanging indent\n"
            "Journal: Author (Year) 'Title', Journal, vol. X, no. Y, pp. Z-Z.\n"
            "Heading: References"
        ),
        "ieee": (
            "IEEE style.\n"
            "In-text: numbered in order of appearance [1], [2]\n"
            "Reference list: numbered, order of citation\n"
            "Journal: [N] A. Author, 'Title,' Journal Abbrev., vol. X, no. Y, pp. Z, Year.\n"
            "Heading: References"
        ),
        "vancouver": (
            "Vancouver style.\n"
            "In-text: superscript numbers in order of appearance\n"
            "Reference list: numbered, order of citation\n"
            "Journal: Author AB. Title. Journal Abbrev. Year;Vol(Issue):pages.\n"
            "Heading: References"
        ),
        "oscola": (
            "OSCOLA — footnote citations, not in-text.\n"
            "Cases: Case Name [Year] Volume Report Page\n"
            "Statutes: Statute Name Year, s Section\n"
            "Articles: Author, 'Title' (Year) Volume Journal Page\n"
            "NEVER fabricate case names or statutes.\n"
            "Heading: Bibliography"
        ),
        "chicago": (
            "Chicago/Turabian.\n"
            "In-text: (Author Year) or footnotes\n"
            "Reference list: alphabetical\n"
            "Journal: Author. 'Title.' Journal Volume, no. Issue (Year): pages.\n"
            "Heading: Bibliography"
        ),
        "mla": (
            "MLA 9th Edition.\n"
            "In-text: (Author page)\n"
            "Reference list: alphabetical\n"
            "Journal: Author. 'Title.' Journal, vol. X, no. Y, Year, pp. Z-Z.\n"
            "Heading: Works Cited"
        ),
    }
    return rules.get(style, rules["apa7"])


def _get_department_rules(dept: str, faculty: str) -> str:
    if "law" in dept or faculty == "law":
        return (
            "LAW: OSCOLA citations, essay format not 5-chapter structure.\n"
            "NEVER fabricate case law, statutes, or legal authorities.\n"
            "Every legal authority must be real and verifiable.\n"
            "Use proper legal citation: Case Name [Year] Court/Report."
        )
    if faculty == "health_sciences" or any(d in dept for d in ["medicine", "nursing", "pharmacy", "medical"]):
        return (
            "HEALTH SCIENCES: Vancouver citations.\n"
            "NEVER make clinical recommendations or suggest dosages.\n"
            "NEVER fabricate clinical data or patient outcomes.\n"
            "Qualify all clinical claims: 'According to FMOH guidelines...'\n"
            "Reference NCDC, FMOH, WHO Nigeria, NAFDAC as primary Nigerian sources."
        )
    if faculty == "engineering_tech" or any(d in dept for d in ["engineering", "engineer", "mechatronics"]):
        return (
            "ENGINEERING: Chapter 4 requires real experimental data — never fabricate.\n"
            "System design chapters must describe actual specifications.\n"
            "IEEE citation style is standard.\n"
            "Reference relevant Nigerian standards where applicable."
        )
    if any(d in dept for d in ["account", "finance", "banking", "economics"]):
        return (
            "ACCOUNTING/FINANCE: Formal H0/Hi null and alternate hypotheses required.\n"
            "Must reference CBN, SEC, FIRS, or NDIC data in Background to Study.\n"
            "Statistical analysis must include regression or correlation output.\n"
            "Interpret both statistical and economic significance of findings."
        )
    if any(d in dept for d in ["computer sci", "software", "data science", "cyber", "info sys"]):
        return (
            "CS/IT: IEEE citation style standard.\n"
            "May use 6-chapter format with System Design and Implementation split.\n"
            "Technical descriptions must be precise and implementable.\n"
            "Reference Nigerian digital economy: NCC, NITDA, fintech landscape."
        )
    return (
        "GENERAL: Follow 5-chapter Nigerian university format.\n"
        "Reference relevant Nigerian institutions and data sources throughout.\n"
        "Ensure findings connect to Nigerian policy and practice implications."
    )


# ─── QUESTIONNAIRE GENERATION ─────────────────────────────────────────────────

async def generate_questionnaire(brief: dict) -> str:
    print(f"[claude] generate_questionnaire: '{brief.get('topic', '')[:60]}'")
    prompt = f"""Generate a complete research questionnaire for this Nigerian final year project:

Topic: {brief.get('topic')}
Research Question: {brief.get('research_question')}
Population: {brief.get('population')}
Research Design: {brief.get('research_type')}
Department: {brief.get('department')}
University: {brief.get('university')}

Structure:
1. Cover letter guaranteeing anonymity and explaining purpose
2. Section A: Demographics (5-6 items appropriate for this population)
3. Section B onwards: Research questions aligned to objectives

Requirements:
- 5-point Likert scale for attitudinal questions
- Minimum 25 items, maximum 40
- Simple clear language for Nigerian respondents
- Number all items clearly
- Thank-you note at the end
- Format clearly for printing and administration"""

    try:
        response = await client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[claude] generate_questionnaire ERROR: {e}")
        raise


# ─── CITATION QUERY GENERATION ────────────────────────────────────────────────

async def generate_citation_queries(brief: dict) -> list[str]:
    print(f"[claude] generate_citation_queries: '{brief.get('topic', '')[:60]}'")
    prompt = f"""Preparing a literature review for this Nigerian final year project:

Topic: {brief.get('topic')}
Research Question: {brief.get('research_question')}
Department: {brief.get('department')}
Research Design: {brief.get('research_type')}

Generate exactly 8 specific academic search queries to find real published papers.
Each query targets a different key concept or claim needed for this literature review.
Mix general theoretical queries with Nigeria/Africa-specific queries.
4-8 words each. Make them specific enough to return relevant papers.

Respond ONLY with a JSON array of exactly 8 strings. Nothing else.
["query one", "query two", ...]"""

    try:
        response = await client.messages.create(
            model=MODEL_INTAKE,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Try parsing as array directly
        if raw.startswith("["):
            try:
                queries = json.loads(raw)
                if isinstance(queries, list):
                    print(f"[claude] Generated {len(queries)} citation queries.")
                    return queries[:8]
            except Exception:
                pass
        # Try extracting from JSON object
        parsed = _extract_json(raw)
        if isinstance(parsed, list):
            return parsed[:8]
        return _fallback_queries(brief)
    except Exception as e:
        print(f"[claude] generate_citation_queries ERROR: {e}")
        return _fallback_queries(brief)


def _fallback_queries(brief: dict) -> list[str]:
    words = brief.get("topic", "").split()[:4]
    dept  = brief.get("department", "")
    return [
        " ".join(words),
        f"{' '.join(words[:3])} Nigeria",
        f"{dept} research Nigeria",
        f"{brief.get('research_question', '')[:50]}",
    ]


# ─── CORRECTION AGENT ─────────────────────────────────────────────────────────

async def run_correction_agent(
    mode: str,
    chapter_number: int,
    chapter_content: str,
    correction_request: str,
    correction_history: list[dict] = None,
) -> str:
    print(f"[claude] run_correction_agent: mode={mode} ch={chapter_number}")

    chapter_names = {
        1: "Introduction",
        2: "Review of Related Literature",
        3: "Research Methodology",
        4: "Data Presentation, Analysis and Discussion of Findings",
        5: "Summary, Conclusion and Recommendations",
    }
    chapter_name = chapter_names.get(chapter_number, f"Chapter {chapter_number}")

    history_text = ""
    if correction_history:
        history_text = "\n\nPREVIOUS CORRECTIONS THIS SESSION:\n"
        for item in correction_history:
            history_text += f"Round {item['round']}: {item['request'][:150]}\n"

    if mode == "understand":
        prompt = f"""A Nigerian final year student wants corrections to 
Chapter {chapter_number} ({chapter_name}).

CORRECTION REQUEST:
"{correction_request}"

CHAPTER CONTENT (first 1500 chars):
{chapter_content[:1500]}
{history_text}

Summarise in clear numbered bullet points exactly what needs to change.
Be specific — not "improve the introduction" but exactly which section 
and what to change about it. Maximum 6 points. Do NOT rewrite yet."""

        try:
            response = await client.messages.create(
                model=MODEL_INTAKE,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            result = response.content[0].text.strip()
            print(f"[claude] Correction understanding: {result[:100]}")
            return result
        except Exception as e:
            print(f"[claude] run_correction_agent understand ERROR: {e}")
            return "I understood what needs to change. Shall I proceed?"

    elif mode == "correct":
        prompt = f"""Edit this Nigerian final year project chapter based on 
student and supervisor feedback. Apply the writing style benchmark.

CHAPTER {chapter_number}: {chapter_name}

ORIGINAL CHAPTER:
{chapter_content}
{history_text}

CORRECTION REQUEST:
"{correction_request}"

{NIGERIAN_ACADEMIC_WRITING_BENCHMARK}

INSTRUCTIONS:
1. Apply ALL corrections thoroughly
2. Maintain same structure and section numbering
3. Keep Nigerian academic standards throughout
4. Preserve valid content not flagged for correction
5. Add genuine depth where asked — not filler sentences
6. Fix citation format if asked — never invent new citations
7. If asked to reduce AI-sounding language — apply the writing benchmark above
8. Return the COMPLETE corrected chapter — not just changed sections

Write the complete corrected chapter now:"""

        try:
            response = await client.messages.create(
                model=MODEL_CHAPTER_2,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            result = response.content[0].text.strip()
            print(f"[claude] Correction applied. Length: {len(result)}")
            return result
        except Exception as e:
            print(f"[claude] run_correction_agent correct ERROR: {e}")
            return ""

    return ""


# ─── CONVERSATION AGENT ───────────────────────────────────────────────────────

async def run_conversation_agent(
    history: list[dict],
    brief: dict,
    user: dict,
    project: dict,
) -> dict:
    print(f"[claude] run_conversation_agent: {len(history)} turns")

    from utils.helpers import summarise_brief_for_prompt
    brief_text = summarise_brief_for_prompt(brief)
    chapter_summary = "\n".join([
        f"Chapter {i}: {'✅ Generated' if project.get(f'chapter_{i}_content') else '⏳ Not yet generated'}"
        for i in range(1, 6)
    ])

    system_prompt = f"""You are FYP Mentor — an intelligent Nigerian academic research assistant.
You are in a live conversation with a subscribed student working on their final year project.

{brief_text}

PROJECT STATUS:
{chapter_summary}

YOUR CAPABILITIES:
1. Answer any question about research, methodology, citations, academic writing
2. Edit any chapter based on supervisor feedback or student corrections
3. Explain academic concepts in context of their specific project
4. Help decode supervisor feedback — translate it into actionable changes
5. Proactively suggest improvements they haven't thought of
6. Guide through difficult sections
7. Help with formatting, citation, structure

WHEN STUDENT WANTS TO EDIT A CHAPTER:
- Identify which chapter (1-5)
- Understand what specifically needs to change
- Summarise clearly in your reply
- Set action to "edit_chapter"

RESPONSE FORMAT — respond ONLY with valid JSON, nothing outside it:
{{
  "reply": "Your conversational response — this is ALL the student sees",
  "action": "none",
  "action_data": {{}}
}}

For chapter edits:
{{
  "reply": "I understand — I will fix [specific things] in Chapter X. Applying now...",
  "action": "edit_chapter",
  "action_data": {{
    "chapter_number": 1,
    "correction_summary": "detailed description of every change to make"
  }}
}}

For chapter generation:
{{
  "reply": "Generating Chapter 3 now...",
  "action": "generate_chapter",
  "action_data": {{"chapter_number": 3}}
}}

For PDF:
{{
  "reply": "Generating your PDF now...",
  "action": "download_pdf",
  "action_data": {{}}
}}

RULES:
- Be warm, direct, conversational — like a supervisor who genuinely cares
- Reference their topic and Nigerian context naturally
- Never be generic — every response tailored to THIS student
- Keep replies concise — this is a chat not an essay
- Never expose the JSON to the student"""

    raw = ""
    try:
        response = await client.messages.create(
            model=MODEL_INTAKE,
            max_tokens=1024,
            system=system_prompt,
            messages=history,
        )
        raw    = response.content[0].text.strip()
        print(f"[claude] Conversation agent raw: {raw[:200]}")
        parsed = _extract_json(raw)

        if not parsed:
            raise ValueError("Empty parse result")

        return {
            "reply":       parsed.get("reply") or _safe_reply(raw, parsed),
            "action":      parsed.get("action", "none"),
            "action_data": parsed.get("action_data", {}),
        }

    except Exception as e:
        print(f"[claude] run_conversation_agent ERROR: {e}")
        clean = _safe_reply(raw, {}) if raw else "I am having a moment — could you repeat that?"
        return {
            "reply":       clean,
            "action":      "none",
            "action_data": {},
        }


print("[claude_service.py] Claude service loaded.")