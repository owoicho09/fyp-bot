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
        # Try direct parse first
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    try:
        # Strip markdown fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass
    try:
        # Find the outermost JSON object anywhere in the text
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group(0))
    except json.JSONDecodeError:
        pass
    print(f"[claude] _extract_json: all parse attempts failed. Raw: {raw[:200]}")
    return {}


def _safe_reply(raw: str, parsed: dict) -> str:
    """
    Extract the reply field from parsed JSON.
    If parsing failed, strip any JSON block from raw and return the remainder.
    Never returns raw JSON to the student.
    """
    reply = parsed.get("reply", "")
    if reply:
        return reply
    # Remove any JSON block from raw text
    clean = re.sub(r"\{[\s\S]*\}", "", raw).strip()
    return clean if clean else "Could you say that again?"


# ─── INTAKE AGENT ─────────────────────────────────────────────────────────────

async def run_intake_agent(
    conversation_history: list[dict],
    student_context: dict,
) -> dict:
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
            "reply":          "I'm having a moment — could you repeat that?",
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

    return f"""You are the intake agent for FYP Mentor, helping Nigerian university final year students set up their research project.

WHAT YOU ALREADY KNOW:
{known_text}

YOUR JOB:
Extract the student's research topic and as much context as possible from what they tell you.
You get ONE follow-up question maximum — use it wisely.

WHAT TO EXTRACT from their message:
- topic (their exact research topic — do not rephrase or change it)
- research_question (what they are trying to find out)
- population (who or what they are studying, which Nigerian state/city)
- time_frame (e.g. 2019–2024)
- research_type (quantitative/qualitative/mixed — infer from topic if possible)
- citation_style (infer from department if possible)
- nigerian_context (specific Nigerian places, institutions, policies mentioned)
- student_background (what they already know about this topic)

CRITICAL RULES:
1. NEVER suggest a different topic. NEVER tell the student to rephrase their topic.
   Accept whatever topic they give. It is their project, not yours.
2. If you can infer research_type and citation_style from their department and topic, do so silently.
3. Set brief_complete to true if you have: topic + at least 2 of (research_question, population, time_frame, research_type).
4. Your ONE follow-up question should target the single most important missing piece.
   Ask about population/scope if missing. Ask about time frame if missing.
   Never ask about citation style or research design — infer these.
5. Keep your reply warm and brief — one or two sentences max.

RESPONSE FORMAT — always respond in this exact JSON:
{{
  "reply": "Your brief warm message to the student",
  "extracted": {{
    "topic": "their topic exactly as stated — omit if not identified",
    "research_question": "omit if not identified",
    "population": "omit if not identified",
    "time_frame": "omit if not identified",
    "research_type": "quantitative|qualitative|mixed — omit if cannot infer",
    "citation_style": "apa7|harvard|ieee|vancouver|oscola|chicago|mla — omit if cannot infer",
    "nigerian_context": "omit if not mentioned",
    "student_background": "omit if not mentioned"
  }},
  "brief_complete": false
}}

Set brief_complete to true as soon as you have enough. Do not fish for more information."""

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

Evaluate against: specificity, researchability, Nigerian/African relevance, originality.

Respond ONLY in this exact JSON:
{{
  "is_valid": true or false,
  "feedback": "One or two sentences of specific constructive feedback",
  "suggestions": ["refined version 1", "refined version 2", "different related topic"]
}}

If is_valid is true, suggestions can be empty list.
If is_valid is false, suggestions must have exactly 3 items."""

    try:
        response = await client.messages.create(
            model=MODEL_INTAKE,
            max_tokens=512,
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
    prompt = f"""A Nigerian final year student needs a research design recommendation.
Topic: {topic}
Department: {department}
Research question: {research_question}

Recommend quantitative, qualitative, or mixed methods.
Give a 2-3 sentence explanation and state the recommended data collection method.
Keep it concise and practical."""

    try:
        response = await client.messages.create(
            model=MODEL_INTAKE,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[claude] recommend_research_design ERROR: {e}")
        return "Quantitative research design is recommended, using a structured questionnaire."


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
        prev_text = "\n\nPREVIOUSLY GENERATED CHAPTERS (for consistency):\n"
        for ch_num, ch_content in previous_chapters.items():
            preview = ch_content[:800] + "..." if len(ch_content) > 800 else ch_content
            prev_text += f"\n--- Chapter {ch_num} (excerpt) ---\n{preview}\n"

    turnitin_instruction = ""
    if brief.get("turnitin"):
        turnitin_instruction = """
TURNITIN-AWARE WRITING:
- Vary sentence lengths throughout
- Vary paragraph opening words — never start consecutive paragraphs with same word
- Use active voice at least 40% of the time
- Use "This study", "The researcher", "The study" for self-reference
- Avoid: "It is worth noting", "It is important to", "Notably", "Furthermore" every paragraph
- Use Nigerian-specific vocabulary, institutions, references naturally
- Weave in the student's own phrasing from their background where possible"""

    level_instruction = {
        "bsc":   "Undergraduate level — clear, structured, academic but not overly complex.",
        "hnd":   "HND level — practical focus, clear structure, applied examples.",
        "pgd":   "Postgraduate diploma — more analytical than undergraduate.",
        "msc":   "Masters level — sophisticated analysis, theoretical depth, critical engagement.",
        "mba":   "MBA level — managerial implications, business context, evidence-based.",
        "mpa":   "MPA level — public policy focus, governance implications.",
        "phd":   "Doctoral level — original contribution, deep theoretical grounding.",
        "noun":  "NOUN level — clear structure, practical examples, accessible academic language.",
    }.get(brief.get("academic_level", "bsc"), "Undergraduate level.")

    return f"""You are an expert Nigerian academic research writer with 20 years supervising final year projects.

{brief_text}

{stats_text}
{prev_text}

ABSOLUTE RULES — NEVER VIOLATE:
1. NEVER invent a citation — only use papers from the provided list
2. NEVER fabricate data, statistics, or research findings
3. ALWAYS reference Nigerian context throughout
4. ALWAYS maintain consistency with Chapter 1 objectives, questions, hypotheses
5. ALWAYS use citation style: {brief.get('citation_style', 'apa7').upper()}
6. ALWAYS write formal academic English for {brief.get('university', 'a Nigerian university')}
7. For Law: NEVER fabricate case law or statutes
8. For Medicine/Health: NEVER make clinical recommendations
9. For Engineering: NEVER fabricate experimental data
10. NEVER write a summary instead of a full chapter

LEVEL: {level_instruction}
DEPARTMENT: {brief.get('department', '')}
{turnitin_instruction}

STRUCTURE:
- Numbered headings and subheadings (1.1, 1.2, etc.)
- Minimum 3 paragraphs per major section
- Transitional sentences between sections
- End with transition to next chapter"""


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
1. Cover letter guaranteeing anonymity
2. Section A: Demographics (5–6 items)
3. Section B+: Research questions aligned to objectives

Requirements:
- 5-point Likert scale for attitudinal questions
- Minimum 25 items, maximum 40
- Simple clear language for Nigerian respondents
- Thank-you note at the end"""

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
Each query targets a different key claim or concept needed for this literature review.

Rules:
- 4–8 words each
- Mix general theoretical queries with Nigeria/Africa-specific queries
- Specific enough to return relevant papers

Respond ONLY with a JSON array of exactly 8 strings. No other text.
["query one", "query two", ...]"""

    try:
        response = await client.messages.create(
            model=MODEL_INTAKE,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw    = response.content[0].text.strip()
        parsed = _extract_json(raw)
        if isinstance(parsed, list):
            print(f"[claude] Generated {len(parsed)} citation queries.")
            return parsed[:8]
        # Try parsing as raw list string
        queries = json.loads(raw) if raw.startswith("[") else []
        if isinstance(queries, list):
            return queries[:8]
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
        prompt = f"""A Nigerian final year student wants corrections to Chapter {chapter_number} ({chapter_name}).

CORRECTION REQUEST:
"{correction_request}"

CHAPTER CONTENT (first 1500 chars):
{chapter_content[:1500]}
{history_text}

Summarise in clear numbered bullet points exactly what needs to change.
Be specific — not "improve the introduction" but "add CBN 2024 statistics to paragraph 2 of Background".
Maximum 6 points. Do NOT rewrite yet."""

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
        prompt = f"""Edit this Nigerian final year project chapter based on feedback.

CHAPTER {chapter_number}: {chapter_name}

ORIGINAL CHAPTER:
{chapter_content}
{history_text}

CORRECTION REQUEST:
"{correction_request}"

INSTRUCTIONS:
1. Apply ALL corrections thoroughly
2. Maintain same structure and section numbering
3. Keep Nigerian academic standards
4. Preserve valid content not flagged for correction
5. Add genuine depth where asked — not filler
6. Fix citation format if asked — never invent new citations
7. Rewrite AI-sounding sections in authentic Nigerian student voice if asked
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
4. Help decode supervisor feedback
5. Suggest improvements proactively
6. Guide through difficult sections
7. Help with formatting, citation style, structure

WHEN STUDENT WANTS TO EDIT A CHAPTER:
- Identify which chapter (1-5)
- Understand what specifically needs to change
- Summarise clearly in your reply
- Set action to "edit_chapter"

RESPONSE FORMAT — always respond in this EXACT JSON. No text outside the JSON:
{{
  "reply": "Your response here — this is ALL the student sees",
  "action": "none",
  "action_data": {{}}
}}

For chapter edits:
{{
  "reply": "I understand — I'll fix [specific things] in Chapter X. Applying now...",
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

For PDF download:
{{
  "reply": "Generating your PDF now...",
  "action": "download_pdf",
  "action_data": {{}}
}}

RULES:
- Respond ONLY with valid JSON — nothing before or after
- "reply" is the ONLY thing the student sees
- Be warm, direct, conversational — like a supervisor who cares
- Reference their topic and Nigerian context naturally
- Never be generic — every response tailored to THIS student
- Keep replies concise"""

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
        # Strip JSON from raw before sending to student
        clean = _safe_reply(raw, {}) if raw else "I'm having a moment — could you repeat that?"
        return {
            "reply":       clean,
            "action":      "none",
            "action_data": {},
        }


print("[claude_service.py] Claude service loaded.")
