print("[keyboards.py] Loading keyboard builders...")

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.constants import (
    ACADEMIC_LEVELS, FACULTIES, RESEARCH_DESIGNS,
    CITATION_STYLES, CHAPTER_NAMES,
)
from config import PLANS


# ─── ONBOARDING ───────────────────────────────────────────────────────────────

def level_keyboard() -> InlineKeyboardMarkup:
    print("[keyboards] level_keyboard")
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"level_{key}")]
        for key, label in ACADEMIC_LEVELS.items()
    ]
    return InlineKeyboardMarkup(buttons)


def faculty_keyboard() -> InlineKeyboardMarkup:
    print("[keyboards] faculty_keyboard")
    items = list(FACULTIES.items())
    buttons = []
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"faculty_{items[i][0]}")]
        if i + 1 < len(items):
            row.append(InlineKeyboardButton(
                items[i + 1][1], callback_data=f"faculty_{items[i + 1][0]}"
            ))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def citation_year_keyboard() -> InlineKeyboardMarkup:
    """
    Citation year range selection during onboarding.
    Default is last 5 years. Student can also type a custom range.
    """
    print("[keyboards] citation_year_keyboard")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Last 5 years (2020–2025) ✅ Recommended", callback_data="cite_year_2020")],
        [InlineKeyboardButton("Last 10 years (2015–2025)",               callback_data="cite_year_2015")],
        [InlineKeyboardButton("Last 15 years (2010–2025)",               callback_data="cite_year_2010")],
        [InlineKeyboardButton("Any year (no restriction)",               callback_data="cite_year_any")],
    ])


def research_design_keyboard() -> InlineKeyboardMarkup:
    print("[keyboards] research_design_keyboard")
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"design_{key}")]
        for key, label in RESEARCH_DESIGNS.items()
    ]
    return InlineKeyboardMarkup(buttons)


def citation_keyboard() -> InlineKeyboardMarkup:
    print("[keyboards] citation_keyboard")
    items = list(CITATION_STYLES.items())
    buttons = []
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"cite_{items[i][0]}")]
        if i + 1 < len(items):
            row.append(InlineKeyboardButton(
                items[i + 1][1], callback_data=f"cite_{items[i + 1][0]}"
            ))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def turnitin_keyboard() -> InlineKeyboardMarkup:
    print("[keyboards] turnitin_keyboard")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes, we use Turnitin", callback_data="turnitin_yes")],
        [InlineKeyboardButton("No / Not sure",        callback_data="turnitin_no")],
    ])


def skip_keyboard(callback_data: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Skip ➡️", callback_data=callback_data)
    ]])


def confirm_brief_keyboard() -> InlineKeyboardMarkup:
    print("[keyboards] confirm_brief_keyboard")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Generate Chapter 1: Introduction",
            callback_data="gen_chapter_1",
        )],
        [InlineKeyboardButton("✏️ Change my topic", callback_data="change_topic")],
        [InlineKeyboardButton("🔄 Start over",       callback_data="restart")],
    ])


# ─── CHAPTER KEYBOARDS ────────────────────────────────────────────────────────

def next_chapter_keyboard(next_chapter: int) -> InlineKeyboardMarkup:
    print(f"[keyboards] next_chapter_keyboard -> ch{next_chapter}")
    name = CHAPTER_NAMES.get(next_chapter, f"Chapter {next_chapter}")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"📖 Generate Chapter {next_chapter}: {name}",
            callback_data=f"gen_chapter_{next_chapter}",
        )],
        [InlineKeyboardButton(
            "📄 Download Word document so far",
            callback_data="download_pdf",
        )],
    ])


def chapter_outline_keyboard(chapter_number: int) -> InlineKeyboardMarkup:
    """
    Shown before each chapter generates.
    Student can drop their own outline or proceed with standard format.
    """
    print(f"[keyboards] chapter_outline_keyboard ch{chapter_number}")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📝 I have an outline / specific instructions",
            callback_data=f"has_outline_{chapter_number}",
        )],
        [InlineKeyboardButton(
            "⚡ Generate with standard format",
            callback_data=f"no_outline_{chapter_number}",
        )],
    ])


def chapter_4_gate_keyboard() -> InlineKeyboardMarkup:
    print("[keyboards] chapter_4_gate_keyboard")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Yes, I have my data ready",
            callback_data="ch4_has_data",
        )],
        [InlineKeyboardButton(
            "📝 Generate questionnaire for me",
            callback_data="ch4_gen_questionnaire",
        )],
        [InlineKeyboardButton(
            "📊 Give me a data entry template",
            callback_data="ch4_gen_template",
        )],
        [InlineKeyboardButton(
            "❓ How do I administer the survey?",
            callback_data="ch4_explain_survey",
        )],
    ])


def download_keyboard() -> InlineKeyboardMarkup:
    """Download button — sends .docx Word document."""
    print("[keyboards] download_keyboard")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "📄 Download Project (.docx)",
            callback_data="download_pdf",
        )
    ]])


# Keep this name so existing code that imports download_pdf_keyboard still works
def download_pdf_keyboard() -> InlineKeyboardMarkup:
    return download_keyboard()


# ─── PAYMENT KEYBOARDS ────────────────────────────────────────────────────────

def payment_plans_keyboard() -> InlineKeyboardMarkup:
    print("[keyboards] payment_plans_keyboard")
    buttons = [
        [InlineKeyboardButton(plan["label"], callback_data=f"pay_{key}")]
        for key, plan in PLANS.items()
    ]
    buttons.append([InlineKeyboardButton(
        "🔍 Check my payment status", callback_data="check_payment",
    )])
    return InlineKeyboardMarkup(buttons)


def payment_link_keyboard(url: str = "") -> InlineKeyboardMarkup:
    """Legacy — kept for compatibility. Now just shows subscribe button."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💳 Subscribe", callback_data="show_plans")
    ]])


# ─── RETURNING USER ───────────────────────────────────────────────────────────

def resume_keyboard(chapters_done: int) -> InlineKeyboardMarkup:
    print(f"[keyboards] resume_keyboard chapters_done={chapters_done}")
    buttons = []
    next_ch = chapters_done + 1
    if next_ch <= 5:
        name = CHAPTER_NAMES.get(next_ch, f"Chapter {next_ch}")
        buttons.append([InlineKeyboardButton(
            f"📖 Continue — Chapter {next_ch}: {name}",
            callback_data=f"gen_chapter_{next_ch}",
        )])
    buttons.append([InlineKeyboardButton(
        "📄 Download Word document so far",
        callback_data="download_pdf",
    )])
    buttons.append([InlineKeyboardButton(
        "🆕 Start a new project",
        callback_data="restart",
    )])
    return InlineKeyboardMarkup(buttons)


def restart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🆕 Start a new project", callback_data="restart")
    ]])


print("[keyboards.py] All keyboard builders loaded.")