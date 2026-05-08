print("[keyboards.py] Loading keyboard builders...")

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.constants import (
    ACADEMIC_LEVELS, FACULTIES, RESEARCH_DESIGNS,
    CITATION_STYLES, CHAPTER_NAMES,
)
from config import PLANS


# ─── ONBOARDING KEYBOARDS ─────────────────────────────────────────────────────

def level_keyboard() -> InlineKeyboardMarkup:
    """Academic level selection — one button per row."""
    print("[keyboards] Building level_keyboard")
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"level_{key}")]
        for key, label in ACADEMIC_LEVELS.items()
    ]
    return InlineKeyboardMarkup(buttons)


def faculty_keyboard() -> InlineKeyboardMarkup:
    """Faculty selection — two per row for compact display."""
    print("[keyboards] Building faculty_keyboard")
    items = list(FACULTIES.items())
    buttons = []
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"faculty_{items[i][0]}")]
        if i + 1 < len(items):
            row.append(
                InlineKeyboardButton(items[i + 1][1], callback_data=f"faculty_{items[i + 1][0]}")
            )
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def research_design_keyboard() -> InlineKeyboardMarkup:
    """Research design selection."""
    print("[keyboards] Building research_design_keyboard")
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"design_{key}")]
        for key, label in RESEARCH_DESIGNS.items()
    ]
    return InlineKeyboardMarkup(buttons)


def citation_keyboard() -> InlineKeyboardMarkup:
    """Citation style selection — two per row."""
    print("[keyboards] Building citation_keyboard")
    items = list(CITATION_STYLES.items())
    buttons = []
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"cite_{items[i][0]}")]
        if i + 1 < len(items):
            row.append(
                InlineKeyboardButton(items[i + 1][1], callback_data=f"cite_{items[i + 1][0]}")
            )
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ─── TOPIC INTAKE QUICK-REPLY OPTIONS ─────────────────────────────────────────
# These appear during the intake conversation to speed up common answers.
# Student can always ignore buttons and type or send a voice note instead.

def yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Generic yes/no keyboard with custom callback data."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Yes", callback_data=yes_data),
        InlineKeyboardButton("No",  callback_data=no_data),
    ]])


def turnitin_keyboard() -> InlineKeyboardMarkup:
    """Does the student's school use Turnitin?"""
    print("[keyboards] Building turnitin_keyboard")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Yes, we use Turnitin",       callback_data="turnitin_yes"),
        InlineKeyboardButton("No / Not sure",              callback_data="turnitin_no"),
    ]])


def research_design_followup_keyboard() -> InlineKeyboardMarkup:
    """Quick pick for research design during intake follow-up."""
    print("[keyboards] Building research_design_followup_keyboard")
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"design_{key}")]
        for key, label in RESEARCH_DESIGNS.items()
    ]
    return InlineKeyboardMarkup(buttons)


def skip_keyboard(callback_data: str = "skip") -> InlineKeyboardMarkup:
    """A single skip button for optional questions."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Skip this question", callback_data=callback_data)
    ]])


def voice_or_text_hint_keyboard() -> InlineKeyboardMarkup:
    """
    Shown when we want to remind the student they can send a voice note.
    Not functional buttons — just a visual prompt with a skip option.
    """
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Skip this question", callback_data="skip_followup")
    ]])


# ─── BRIEF CONFIRMATION KEYBOARD ──────────────────────────────────────────────

def confirm_brief_keyboard() -> InlineKeyboardMarkup:
    """Shown after the full project brief is summarised."""
    print("[keyboards] Building confirm_brief_keyboard")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Generate Chapter 1: Introduction",
            callback_data="gen_chapter_1"
        )],
        [InlineKeyboardButton(
            "✏️ Change my topic",
            callback_data="change_topic"
        )],
        [InlineKeyboardButton(
            "🔄 Start over",
            callback_data="restart"
        )],
    ])


# ─── CHAPTER KEYBOARDS ────────────────────────────────────────────────────────

def next_chapter_keyboard(next_chapter: int) -> InlineKeyboardMarkup:
    """Shown after a chapter is delivered."""
    print(f"[keyboards] Building next_chapter_keyboard for chapter {next_chapter}")
    name = CHAPTER_NAMES.get(next_chapter, f"Chapter {next_chapter}")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"Generate Chapter {next_chapter}: {name}",
            callback_data=f"gen_chapter_{next_chapter}"
        )],
        [InlineKeyboardButton(
            "📄 Download PDF so far",
            callback_data="download_pdf"
        )],
    ])


def chapter_4_gate_keyboard() -> InlineKeyboardMarkup:
    """Shown before Chapter 4 — data collection gate."""
    print("[keyboards] Building chapter_4_gate_keyboard")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Yes, I have my data ready",
            callback_data="ch4_has_data"
        )],
        [InlineKeyboardButton(
            "📝 Generate questionnaire for me",
            callback_data="ch4_gen_questionnaire"
        )],
        [InlineKeyboardButton(
            "📊 Give me a data entry template",
            callback_data="ch4_gen_template"
        )],
        [InlineKeyboardButton(
            "❓ How do I administer the survey?",
            callback_data="ch4_explain_survey"
        )],
    ])


def download_pdf_keyboard() -> InlineKeyboardMarkup:
    """Shown after all chapters are complete."""
    print("[keyboards] Building download_pdf_keyboard")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📥 Download Full Project PDF",
            callback_data="download_pdf"
        )],
    ])


# ─── PAYMENT KEYBOARDS ────────────────────────────────────────────────────────

def payment_plans_keyboard() -> InlineKeyboardMarkup:
    """Paywall — shown after Chapter 2 is delivered."""
    print("[keyboards] Building payment_plans_keyboard")
    buttons = [
        [InlineKeyboardButton(plan["label"], callback_data=f"pay_{key}")]
        for key, plan in PLANS.items()
    ]
    buttons.append([
        InlineKeyboardButton(
            "🔍 Check my payment status",
            callback_data="check_payment"
        )
    ])
    return InlineKeyboardMarkup(buttons)


def payment_link_keyboard(url: str) -> InlineKeyboardMarkup:
    """Shown after a Paystack link is generated."""
    print("[keyboards] Building payment_link_keyboard")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay now (Paystack)", url=url)],
        [InlineKeyboardButton("✅ I've paid — check status", callback_data="check_payment")],
    ])


# ─── RETURNING USER KEYBOARD ──────────────────────────────────────────────────

def resume_keyboard(chapters_done: int) -> InlineKeyboardMarkup:
    """Shown to a returning user who has an active project."""
    print(f"[keyboards] Building resume_keyboard, chapters_done={chapters_done}")
    buttons = []
    next_ch = chapters_done + 1
    if next_ch <= 5:
        name = CHAPTER_NAMES.get(next_ch, f"Chapter {next_ch}")
        buttons.append([InlineKeyboardButton(
            f"Continue — Chapter {next_ch}: {name}",
            callback_data=f"gen_chapter_{next_ch}"
        )])
    buttons.append([InlineKeyboardButton(
        "📄 Download PDF so far",
        callback_data="download_pdf"
    )])
    buttons.append([InlineKeyboardButton(
        "🆕 Start a new project",
        callback_data="restart"
    )])
    return InlineKeyboardMarkup(buttons)


def restart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🆕 Start a new project", callback_data="restart")
    ]])


print("[keyboards.py] All keyboard builders loaded.")