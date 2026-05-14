print("[helpers.py] Loading helper utilities...")

import re
from typing import List, Optional
from telegram import Bot
from utils.constants import (
    TELEGRAM_MAX_LENGTH, MIN_TOPIC_WORDS, MAX_TOPIC_WORDS,
    ACADEMIC_LEVELS, FACULTIES, CITATION_STYLES, CHAPTER_NAMES,
)


# ─── MESSAGE SPLITTING ────────────────────────────────────────────────────────

def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> List[str]:
    """
    Split a long message into Telegram-safe chunks.
    Breaks at paragraph boundaries first, then sentence boundaries.
    Numbers parts if more than one chunk is needed.
    """
    print(f"[helpers] split_message called. Text length: {len(text)}")
    if len(text) <= max_length:
        return [text]

    parts = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        # +2 for the \n\n we'll add between paragraphs
        if len(current) + len(para) + 2 <= max_length:
            current += ("\n\n" if current else "") + para
        else:
            if current:
                parts.append(current.strip())
            # Single paragraph too long — split at sentence boundaries
            if len(para) > max_length:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current = ""
                for sentence in sentences:
                    if len(current) + len(sentence) + 1 <= max_length:
                        current += (" " if current else "") + sentence
                    else:
                        if current:
                            parts.append(current.strip())
                        current = sentence
            else:
                current = para

    if current:
        parts.append(current.strip())

    # Number parts if more than one
    if len(parts) > 1:
        total = len(parts)
        numbered = []
        for i, part in enumerate(parts, 1):
            numbered.append(f"*Part {i}/{total}*\n\n{part}")
        print(f"[helpers] Message split into {total} parts.")
        return numbered

    return parts


async def send_long_message(
    bot: Bot,
    chat_id: int,
    text: str,
    parse_mode: str = "Markdown",
    reply_markup=None,
) -> None:
    """
    Send a message, automatically splitting if it exceeds Telegram's limit.
    reply_markup is only attached to the final part.
    """
    print(f"[helpers] send_long_message to chat_id={chat_id}, length={len(text)}")
    parts = split_message(text)
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        await bot.send_message(
            chat_id=chat_id,
            text=part,
            parse_mode=parse_mode,
            reply_markup=reply_markup if is_last else None,
        )


# ─── TOPIC VALIDATION (lightweight — deep validation done by Claude) ──────────

def is_topic_too_short(topic: str) -> bool:
    return len(topic.strip().split()) < MIN_TOPIC_WORDS


def is_topic_too_long(topic: str) -> bool:
    return len(topic.strip().split()) > MAX_TOPIC_WORDS


def clean_topic(topic: str) -> str:
    """Strip, normalise whitespace, and capitalise first letter."""
    topic = topic.strip()
    topic = re.sub(r'\s+', ' ', topic)
    if topic:
        topic = topic[0].upper() + topic[1:]
    return topic


def looks_like_question(text: str) -> bool:
    """Check if the student sent a question instead of a topic statement."""
    stripped = text.strip().lower()
    return (
        stripped.endswith("?") or
        stripped.startswith(("what ", "how ", "why ", "when ", "where ", "which ", "can ", "is "))
    )


# ─── PROJECT BRIEF FORMATTING ─────────────────────────────────────────────────

def format_project_brief(brief: dict) -> str:
    """
    Format the assembled project brief into a readable Telegram message
    shown to the student for confirmation before Chapter 1 is generated.
    """
    print("[helpers] format_project_brief called")

    level        = ACADEMIC_LEVELS.get(brief.get("academic_level", ""), brief.get("academic_level", "—"))
    faculty      = FACULTIES.get(brief.get("faculty", ""), brief.get("faculty", "—"))
    department   = brief.get("department", "—")
    university   = brief.get("university", "—")
    topic        = brief.get("topic", "—")
    research_q   = brief.get("research_question", "")
    population   = brief.get("population", "")
    time_frame   = brief.get("time_frame", "")
    design       = brief.get("research_type", "—").replace("_", " ").title()
    citation     = CITATION_STYLES.get(brief.get("citation_style", ""), "—")
    objectives   = brief.get("objectives", [])
    turnitin     = brief.get("turnitin", False)
    supervisor   = brief.get("supervisor_context", "")

    lines = [
        "📋 *Your Project Brief*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"*Level:* {level}",
        f"*Faculty:* {faculty}",
        f"*Department:* {department}",
        f"*University:* {university}",
        "",
        f"*Topic:*",
        f"_{topic}_",
    ]

    if research_q:
        lines += ["", f"*Core Research Question:*", f"_{research_q}_"]

    if population:
        lines += ["", f"*Population / Scope:* {population}"]

    if time_frame:
        lines += [f"*Time Frame:* {time_frame}"]

    if objectives:
        lines += ["", "*Objectives:*"]
        for i, obj in enumerate(objectives, 1):
            lines.append(f"{i}. {obj}")

    lines += [
        "",
        f"*Research Design:* {design}",
        f"*Citation Style:* {citation}",
        f"*Turnitin Check:* {'Yes — AI-aware writing enabled' if turnitin else 'No / Not confirmed'}",
    ]

    if supervisor:
        lines += ["", f"*Supervisor Notes:* _{supervisor}_"]

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "_Chapters 1 and 2 are completely free._",
        "Tap below to generate Chapter 1, or change your topic if needed.",
    ]

    return "\n".join(lines)


def format_chapter_intro(chapter_number: int, topic: str) -> str:
    """Header message sent to student before a chapter starts generating."""
    print(f"[helpers] format_chapter_intro for chapter {chapter_number}")
    name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")
    return (
        f"📖 *Chapter {chapter_number}: {name}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_{topic}_\n\n"
        f"Generating now — this takes 30–90 seconds depending on chapter length.\n"
        f"Please wait... ⏳"
    )


def format_chapter_disclaimer() -> str:
    """Mandatory disclaimer appended after every generated chapter."""
    return (
        "\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *Important Notice*\n"
        "This chapter was generated by AI to support your research process. "
        "You must read through the entire chapter, verify all facts, figures, "
        "and citations, rewrite sections in your own voice, and have it reviewed "
        "by your supervisor before submission. "
        "Submitting AI-generated content without substantial personal editing "
        "is an academic integrity violation. "
        "This tool is a research assistant — not a submission service."
    )


def format_paywall_message() -> str:
    """Paywall message shown after Chapter 2 is delivered."""
    print("[helpers] format_paywall_message called")
    return (
        "🎉 *Chapters 1 and 2 are complete!*\n\n"
        "You've seen what FYP Mentor delivers — a structured, contextualised "
        "project with real verified citations, Nigerian data grounding, and "
        "writing calibrated to reduce AI detection.\n\n"
        "To continue with Chapters 3, 4, and 5, choose a plan:\n\n"
        "📌 *Weekly Pass — ₦3,000/week*\n"
        "Chapters 3–5 + all tools\n\n"
        "📌 *Project Pass — ₦7,500 one-time*\n"
        "All chapters + 90 days access _(best value)_\n\n"
        "📌 *Postgrad Pass — ₦10,000/month*\n"
        "MSc/MBA format + extended methodology + priority support\n\n"
        "_Payment is processed securely via Paystack. "
        "Access is granted instantly after confirmation._"
    )


def format_completion_message(topic: str) -> str:
    """Message shown when all 5 chapters are complete."""
    return (
        "🏆 *Your project is complete!*\n\n"
        f"_{topic}_\n\n"
        "All 5 chapters have been generated with:\n"
        "✓ Verified academic citations\n"
        "✓ Nigerian data and context\n"
        "✓ Your university format\n"
        "✓ Consistent objectives, questions, and hypotheses across all chapters\n\n"
        "Download your formatted PDF below. "
        "Remember to read through everything, edit in your own voice, "
        "and review with your supervisor before submission."
    )


# ─── TRANSCRIPT CLEANING ──────────────────────────────────────────────────────

def clean_transcript(transcript: str) -> str:
    """
    Clean a Whisper transcript for use in the intake conversation.
    Removes filler words, normalises whitespace, fixes common Whisper quirks.
    """
    print(f"[helpers] clean_transcript called. Raw length: {len(transcript)}")
    # Remove leading/trailing whitespace
    text = transcript.strip()
    # Normalise multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    # Remove common Whisper artifacts
    text = re.sub(r'\[.*?\]', '', text)         # [Music], [Applause] etc.
    text = re.sub(r'\(.*?\)', '', text)          # (inaudible) etc.
    text = text.strip()
    print(f"[helpers] clean_transcript done. Clean length: {len(text)}")
    return text


# ─── BRIEF EXTRACTION HELPERS ─────────────────────────────────────────────────

def extract_brief_from_context(user_data: dict) -> dict:
    """
    Pull the assembled project brief out of context.user_data
    into a clean dict ready for Supabase and prompt injection.
    """
    print("[helpers] extract_brief_from_context called")
    return {
        "academic_level":    user_data.get("academic_level", ""),
        "faculty":           user_data.get("faculty", ""),
        "department":        user_data.get("department", ""),
        "university":        user_data.get("university", ""),
        "topic":             user_data.get("topic", ""),
        "research_question": user_data.get("research_question", ""),
        "population":        user_data.get("population", ""),
        "time_frame":        user_data.get("time_frame", ""),
        "research_type":     user_data.get("research_type", ""),
        "citation_style":    user_data.get("citation_style", ""),
        "objectives":        user_data.get("objectives", []),
        "hypotheses":        user_data.get("hypotheses", []),
        "turnitin":          user_data.get("turnitin", False),
        "supervisor_context":user_data.get("supervisor_context", ""),
        "nigerian_context":  user_data.get("nigerian_context", ""),
        "student_background":user_data.get("student_background", ""),
        "citation_year_from": user_data.get("citation_year_from", 2019),
        "chapter_format": user_data.get("chapter_format", ""),
    }


def summarise_brief_for_prompt(brief: dict) -> str:
    """
    Compact single-string summary of the project brief injected into
    every Claude system prompt so Claude always has full context.
    """
    print("[helpers] summarise_brief_for_prompt called")
    objectives_text = ""
    if brief.get("objectives"):
        obj_list = "\n".join(f"  {i+1}. {o}" for i, o in enumerate(brief["objectives"]))
        objectives_text = f"\nObjectives:\n{obj_list}"

    hypotheses_text = ""
    if brief.get("hypotheses"):
        hyp_list = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(brief["hypotheses"]))
        hypotheses_text = f"\nHypotheses:\n{hyp_list}"

    return f"""
STUDENT PROJECT BRIEF
=====================
Level      : {brief.get('academic_level', 'Not specified')}
Department : {brief.get('department', 'Not specified')}
University : {brief.get('university', 'Not specified')}
Faculty    : {brief.get('faculty', 'Not specified')}

Topic      : {brief.get('topic', 'Not specified')}
Research Q : {brief.get('research_question', 'Not specified')}
Population : {brief.get('population', 'Not specified')}
Time Frame : {brief.get('time_frame', 'Not specified')}
Design     : {brief.get('research_type', 'Not specified')}
Citation   : {brief.get('citation_style', 'Not specified')}
Turnitin   : {'Yes' if brief.get('turnitin') else 'No'}
{objectives_text}
{hypotheses_text}
Supervisor notes : {brief.get('supervisor_context', 'None provided')}
Nigerian context : {brief.get('nigerian_context', 'None provided')}
Student background: {brief.get('student_background', 'None provided')}
""".strip()


print("[helpers.py] All helper utilities loaded.")

