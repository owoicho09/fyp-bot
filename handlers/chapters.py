print("[chapters.py] Loading chapters handler...")

import json
import re
from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, CommandHandler
)
from services.supabase_service import (
    get_active_project, save_chapter_content, update_project,
    get_verified_references, add_verified_reference, is_subscribed,
)
from services.claude_service import (
    generate_chapter, generate_citation_queries, generate_questionnaire,
)
from services.search_service import (
    find_citations_batch, search_nigerian_stats,
)
from utils.helpers import (
    send_long_message, format_chapter_intro,
    format_chapter_disclaimer, format_paywall_message,
    format_completion_message,
)
from utils.keyboards import (
    next_chapter_keyboard, payment_plans_keyboard,
    chapter_4_gate_keyboard, download_pdf_keyboard,
    restart_keyboard,
)
from utils.prompts.intake_agent import (
    get_generating_message, get_chapter_2_citation_update,
    get_error_message,
)
from utils.constants import CHAPTER_NAMES, FREE_CHAPTERS, PAID_CHAPTERS


# ─── ENTRY POINT FROM ONBOARDING ─────────────────────────────────────────────

async def generate_chapter_1(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called directly from onboarding after brief is confirmed."""
    print(f"[chapters] generate_chapter_1 called from onboarding")
    user_id = query.from_user.id
    await _generate_and_deliver_chapter(
        user_id=user_id,
        chapter_number=1,
        context=context,
        send_target=query.message,
    )


# ─── CALLBACK: gen_chapter_N buttons ─────────────────────────────────────────

async def handle_generate_chapter(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Parse chapter number from callback data
    match = re.match(r"^gen_chapter_(\d+)$", query.data)
    if not match:
        print(f"[chapters] Invalid callback data: {query.data}")
        return

    chapter_number = int(match.group(1))
    print(f"[chapters] handle_generate_chapter: ch={chapter_number} user={user_id}")

    # Check paywall for chapters 3–5
    if chapter_number in PAID_CHAPTERS:
        if not is_subscribed(user_id):
            print(f"[chapters] Paywall hit for user {user_id} on chapter {chapter_number}")
            await query.message.reply_text(
                format_paywall_message(),
                parse_mode="Markdown",
                reply_markup=payment_plans_keyboard(),
            )
            return

    # Chapter 4 data gate
    if chapter_number == 4:
        project = get_active_project(user_id)
        if project and not project.get("student_data"):
            print(f"[chapters] Chapter 4 data gate triggered for user {user_id}")
            await query.message.reply_text(
                "📊 *Before I write Chapter 4, I need your data.*\n\n"
                "Chapter 4 presents and analyses your actual research findings. "
                "I will never fabricate data — that would be academic fraud.\n\n"
                "What would you like to do?",
                parse_mode="Markdown",
                reply_markup=chapter_4_gate_keyboard(),
            )
            return

    await query.edit_message_reply_markup(reply_markup=None)
    await _generate_and_deliver_chapter(
        user_id=user_id,
        chapter_number=chapter_number,
        context=context,
        send_target=query.message,
    )


# ─── CORE GENERATION FUNCTION ─────────────────────────────────────────────────

async def _generate_and_deliver_chapter(
    user_id: int,
    chapter_number: int,
    context: ContextTypes.DEFAULT_TYPE,
    send_target,
) -> None:
    """
    The core function that generates a chapter and delivers it to the student.
    Handles: stats fetching, citation pipeline (ch2), prompt assembly,
    Claude API call, content saving, disclaimer appending, next-step keyboard.
    """
    print(f"[chapters] _generate_and_deliver_chapter: user={user_id} ch={chapter_number}")
    chapter_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")

    # Load project brief from Supabase
    project = get_active_project(user_id)
    if not project:
        await send_target.reply_text(
            "I couldn't find your active project. Please send /start to begin.",
        )
        return

    # Build brief dict from project record
    # Build brief dict — pull user fields as fallback
    from services.supabase_service import get_user
    user = get_user(user_id)
    brief = _project_to_brief(project, user)


    # Send "generating" status message
    status_msg = await send_target.reply_text(
        get_generating_message(chapter_number, chapter_name),
        parse_mode="Markdown",
    )

    # ── Fetch live Nigerian statistics ──────────────────────────────────────
    live_stats = {}
    try:
        print(f"[chapters] Fetching live Nigerian stats for ch{chapter_number}...")
        live_stats = await search_nigerian_stats(brief.get("topic", ""))
        print(f"[chapters] Stats fetched: {len(live_stats)} indicators")
    except Exception as e:
        print(f"[chapters] Stats fetch failed (non-fatal): {e}")

    # ── Citation pipeline (Chapter 2 only) ───────────────────────────────────
    citations = []
    if chapter_number == 2:
        citations = await _run_citation_pipeline(
            brief=brief,
            status_msg=status_msg,
            user_id=user_id,
        )

    # ── Load previous chapters for consistency ────────────────────────────────
    previous_chapters = _load_previous_chapters(project, chapter_number)

    # ── Generate chapter via Claude ───────────────────────────────────────────
    try:
        await status_msg.edit_text(
            f"✍️ Writing Chapter {chapter_number}: {chapter_name}...",
        )
        content = await generate_chapter(
            chapter_number=chapter_number,
            brief=brief,
            citations=citations,
            live_stats=live_stats,
            previous_chapters=previous_chapters,
        )
        print(f"[chapters] Chapter {chapter_number} generated. Length={len(content)}")
    except Exception as e:
        print(f"[chapters] Generation error: {e}")
        await status_msg.edit_text(
            get_error_message(f"generating Chapter {chapter_number}"),
        )
        return

    # ── Extract objectives/hypotheses from Chapter 1 ──────────────────────────
    if chapter_number == 1:
        _extract_and_save_chapter_1_data(user_id, content)
        content = _strip_extracted_data_block(content)

    # ── Check for project complete marker ─────────────────────────────────────
    is_complete = "<!--PROJECT_COMPLETE-->" in content
    if is_complete:
        content = content.replace("<!--PROJECT_COMPLETE-->", "").strip()

    # ── Save chapter to Supabase ──────────────────────────────────────────────
    save_chapter_content(user_id, chapter_number, content)
    print(f"[chapters] Chapter {chapter_number} saved to Supabase.")

    # ── Delete status message ─────────────────────────────────────────────────
    try:
        await status_msg.delete()
    except Exception:
        pass

    # ── Deliver chapter header ────────────────────────────────────────────────
    await send_target.reply_text(
        format_chapter_intro(chapter_number, brief.get("topic", "")),
        parse_mode="Markdown",
    )

    # ── Deliver chapter content (split if needed) ─────────────────────────────
    await send_long_message(
        bot=context.bot,
        chat_id=send_target.chat_id,
        text=content,
        parse_mode="Markdown",
    )

    # ── Append disclaimer ─────────────────────────────────────────────────────
    await send_target.reply_text(
        format_chapter_disclaimer(),
        parse_mode="Markdown",
    )

    # ── Show next step ────────────────────────────────────────────────────────
    if is_complete or chapter_number == 5:
        await send_target.reply_text(
            format_completion_message(brief.get("topic", "")),
            parse_mode="Markdown",
            reply_markup=download_pdf_keyboard(),
        )
    elif chapter_number == 2 and not is_subscribed(user_id):
        # Paywall after Chapter 2
        await send_target.reply_text(
            format_paywall_message(),
            parse_mode="Markdown",
            reply_markup=payment_plans_keyboard(),
        )
    else:
        next_chapter = chapter_number + 1
        await send_target.reply_text(
            f"✅ *Chapter {chapter_number}* is ready!\n\n"
            f"Tap below when you're ready for the next chapter.",
            parse_mode="Markdown",
            reply_markup=next_chapter_keyboard(next_chapter),
        )

    print(f"[chapters] Chapter {chapter_number} delivered to user {user_id}")


# ─── CITATION PIPELINE (Chapter 2) ────────────────────────────────────────────

async def _run_citation_pipeline(
    brief: dict,
    status_msg,
    user_id: int,
) -> list[dict]:
    """
    Run the full citation pipeline for Chapter 2.
    1. Ask Claude to generate search queries for this topic
    2. Run batch search across OpenAlex → Crossref → Semantic Scholar
    3. Save verified references to Supabase
    4. Return citation list for injection into chapter prompt
    """
    print(f"[chapters] Running citation pipeline for user {user_id}")

    try:
        await status_msg.edit_text(
            "🔍 Generating search queries for your literature review..."
        )
        queries = await generate_citation_queries(brief)
        print(f"[chapters] Generated {len(queries)} search queries")

        await status_msg.edit_text(
            f"📚 Searching {len(queries)} academic databases for verified citations..."
        )
        papers = await find_citations_batch(queries, max_per_query=4)
        print(f"[chapters] Found {len(papers)} unique papers")

        # Save to Supabase
        for paper in papers:
            add_verified_reference(user_id, paper)

        # Update status with result
        source = "OpenAlex" if papers else "fallback sources"
        await status_msg.edit_text(
            get_chapter_2_citation_update(len(papers), "openalex" if papers else "none"),
            parse_mode="Markdown",
        )
        return papers

    except Exception as e:
        print(f"[chapters] Citation pipeline error (non-fatal): {e}")
        await status_msg.edit_text(
            "📚 Citation search encountered an issue — writing with available sources..."
        )
        return []


# ─── CHAPTER 4 DATA GATE HANDLERS ─────────────────────────────────────────────

async def handle_ch4_has_data(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"[chapters] ch4_has_data: user={user_id}")

    await query.edit_message_text(
        "Great! Please send me your data now.\n\n"
        "You can paste it as:\n"
        "• A table (copy from Excel/Google Sheets)\n"
        "• A summary of your responses (e.g. '120 respondents, 65% female...')\n"
        "• Raw frequency counts per question\n\n"
        "The more detail you provide, the better the analysis will be.\n\n"
        "Send your data now:",
    )
    context.user_data["awaiting_ch4_data"] = True


async def handle_ch4_data_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Receive student's actual data for Chapter 4."""
    if not context.user_data.get("awaiting_ch4_data"):
        return

    user_id = update.effective_user.id
    data_text = update.message.text.strip()
    print(f"[chapters] Received ch4 data from {user_id}: {len(data_text)} chars")

    if len(data_text) < 20:
        await update.message.reply_text(
            "That doesn't look like enough data. "
            "Please paste your actual survey results or response summary."
        )
        return

    # Save data to project
    update_project(user_id, {"student_data": data_text})
    context.user_data.pop("awaiting_ch4_data", None)

    await update.message.reply_text(
        "✅ Data received. Generating *Chapter 4: Data Presentation, "
        "Analysis and Discussion of Findings* now...\n\n"
        "This takes 60–90 seconds. Please wait ⏳",
        parse_mode="Markdown",
    )

    await _generate_and_deliver_chapter(
        user_id=user_id,
        chapter_number=4,
        context=context,
        send_target=update.message,
    )


async def handle_ch4_gen_questionnaire(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"[chapters] ch4_gen_questionnaire: user={user_id}")

    await query.edit_message_text(
        "Generating your research questionnaire... ⏳"
    )

    project = get_active_project(user_id)
    if not project:
        await query.message.reply_text("Could not find your project. Send /start.")
        return
        # Build brief dict — pull user fields as fallback
    from services.supabase_service import get_user
    user = get_user(user_id)
    brief = _project_to_brief(project, user)
    try:
        questionnaire = await generate_questionnaire(brief)
        await send_long_message(
            bot=context.bot,
            chat_id=query.message.chat_id,
            text=(
                "📋 *Your Research Questionnaire*\n\n"
                + questionnaire
                + "\n\n━━━━━━━━━━━━━━━━━━━━\n"
                "_Administer this to your respondents, collect the responses, "
                "then come back and share your data to generate Chapter 4._"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[chapters] Questionnaire generation error: {e}")
        await query.message.reply_text(
            get_error_message("generating the questionnaire")
        )


async def handle_ch4_gen_template(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"[chapters] ch4_gen_template: user={user_id}")

    project = get_active_project(user_id)
    # handle_ch4_gen_template
    from services.supabase_service import get_user
    user = get_user(user_id)
    brief = _project_to_brief(project, user) if project else {}

    template = (
        "📊 *Data Entry Template*\n\n"
        "Use this format to summarise your collected responses:\n\n"
        "*Section A — Demographics*\n"
        "| Variable | Category | Frequency | % |\n"
        "|----------|----------|-----------|---|\n"
        "| Gender   | Male     | ?         | ? |\n"
        "| Gender   | Female   | ?         | ? |\n"
        "| Age      | 18–25    | ?         | ? |\n"
        "| Age      | 26–35    | ?         | ? |\n\n"
        "*Section B — Research Questions (Likert Scale)*\n"
        "| Item | SA (5) | A (4) | U (3) | D (2) | SD (1) | Mean | Std Dev |\n"
        "|------|--------|-------|-------|-------|--------|------|---------|\n"
        "| Q1   | ?      | ?     | ?     | ?     | ?      | ?    | ?       |\n"
        "| Q2   | ?      | ?     | ?     | ?     | ?      | ?    | ?       |\n\n"
        "*Total respondents:* ?\n"
        "*Questionnaires distributed:* ?\n"
        "*Valid responses returned:* ?\n\n"
        "Fill in the ? values with your actual data, then send it back to me."
    )

    await query.edit_message_text(template, parse_mode="Markdown")


async def handle_ch4_explain_survey(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    print(f"[chapters] ch4_explain_survey: user={query.from_user.id}")

    explanation = (
        "📖 *How to Administer Your Survey*\n\n"
        "*Step 1 — Print or share digitally*\n"
        "Print copies of your questionnaire OR create a Google Form version. "
        "Google Forms is free and easy to share via WhatsApp.\n\n"
        "*Step 2 — Reach your sample*\n"
        "Go to your study location (office, market, school, hospital etc.) "
        "and distribute to your target respondents. "
        "Be polite, explain it's for academic research, and guarantee anonymity.\n\n"
        "*Step 3 — Collect responses*\n"
        "Collect filled questionnaires immediately if paper-based, "
        "or set a 3–5 day deadline for Google Forms.\n\n"
        "*Step 4 — Count your responses*\n"
        "For each question, count how many people chose each option. "
        "Enter the counts into the data template I'll give you.\n\n"
        "*Step 5 — Come back with your data*\n"
        "Once you have your counts, return here and I'll analyse "
        "everything and write Chapter 4 for you.\n\n"
        "How many respondents are you targeting?"
    )

    await query.edit_message_text(explanation, parse_mode="Markdown")


# ─── PDF DOWNLOAD ─────────────────────────────────────────────────────────────

async def handle_download_pdf(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"[chapters] handle_download_pdf: user={user_id}")

    await query.message.reply_text("Generating your PDF... ⏳")

    project = get_active_project(user_id)
    if not project:
        await query.message.reply_text(
            "Could not find your project. Send /start."
        )
        return

    try:
        from services.pdf_service import generate_project_pdf
        from services.supabase_service import get_user

        user = get_user(user_id)
        # Merge user fields into project for PDF title page
        if user:
            project["university"]    = project.get("university")    or user.get("university", "")
            project["department"]    = project.get("department")    or user.get("department", "")
            project["academic_level"]= project.get("academic_level")or user.get("academic_level", "bsc")
            project["faculty"]       = project.get("faculty")       or user.get("faculty", "")

        pdf_buffer = generate_project_pdf(project, user)

        chapters_done = project.get("chapters_completed", 0)
        filename = (
            f"FYP_Mentor_{project['topic'][:30].replace(' ', '_')}"
            f"_Ch1-{chapters_done}.pdf"
        )

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_buffer,
            filename=filename,
            caption=(
                f"📄 *Your project PDF* — Chapters 1–{chapters_done}\n\n"
                "Remember to read through, edit in your own voice, "
                "and review with your supervisor before submission."
            ),
            parse_mode="Markdown",
        )
        print(f"[chapters] PDF sent to user {user_id}")

    except Exception as e:
        print(f"[chapters] PDF generation error: {e}")
        await query.message.reply_text(
            "PDF generation failed. Your chapters are saved — "
            "try again in a moment."
        )


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _project_to_brief(project: dict, user: dict = None) -> dict:
    print(f"[chapters] _project_to_brief: project_id={project.get('id')}")
    u = user or {}

    def _parse(field):
        val = project.get(field, [])
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return []
        return val or []

    return {
        "topic":             project.get("topic", ""),
        "research_question": project.get("research_question", ""),
        "population":        project.get("population", ""),
        "time_frame":        project.get("time_frame", ""),
        "research_type":     project.get("research_type") or u.get("research_type") or "quantitative",
        "citation_style":    project.get("citation_style") or u.get("citation_style") or "apa7",
        "objectives":        _parse("objectives"),
        "hypotheses":        _parse("hypotheses"),
        "turnitin":          project.get("turnitin", False),
        "supervisor_context":project.get("supervisor_context", "") or u.get("supervisor_context", ""),
        "nigerian_context":  project.get("nigerian_context", ""),
        "student_background":project.get("student_background", ""),
        "student_data":      project.get("student_data", ""),
        "department":        project.get("department") or u.get("department") or "",
        "university":        project.get("university") or u.get("university") or "",
        "academic_level":    project.get("academic_level") or u.get("academic_level") or "bsc",
        "faculty":           project.get("faculty") or u.get("faculty") or "",
    }

def _load_previous_chapters(project: dict, current_chapter: int) -> dict:
    """Load previously generated chapter content for consistency injection."""
    prev = {}
    for ch in range(1, current_chapter):
        content = project.get(f"chapter_{ch}_content", "")
        if content:
            prev[ch] = content
    print(f"[chapters] Loaded {len(prev)} previous chapters for context")
    return prev


def _extract_and_save_chapter_1_data(user_id: int, content: str) -> None:
    """
    Extract objectives and hypotheses from Chapter 1's hidden data block
    and save them to the project record for use in subsequent chapters.
    """
    print(f"[chapters] _extract_and_save_chapter_1_data: user={user_id}")
    try:
        match = re.search(
            r"<!--EXTRACTED_DATA\s*(.*?)\s*EXTRACTED_DATA-->",
            content,
            re.DOTALL,
        )
        if not match:
            print("[chapters] No EXTRACTED_DATA block found in Chapter 1")
            return

        data = json.loads(match.group(1))
        objectives  = data.get("objectives", [])
        questions   = data.get("research_questions", [])
        hypotheses  = data.get("hypotheses", [])

        update_project(user_id, {
            "objectives":         json.dumps(objectives),
            "research_questions": json.dumps(questions),
            "hypotheses":         json.dumps(hypotheses),
        })
        print(
            f"[chapters] Saved from Ch1: "
            f"{len(objectives)} objectives, "
            f"{len(questions)} questions, "
            f"{len(hypotheses)} hypotheses"
        )
    except Exception as e:
        print(f"[chapters] _extract_and_save_chapter_1_data error: {e}")


def _strip_extracted_data_block(content: str) -> str:
    """Remove the hidden data extraction block before delivering to student."""
    return re.sub(
        r"<!--EXTRACTED_DATA.*?EXTRACTED_DATA-->",
        "",
        content,
        flags=re.DOTALL,
    ).strip()


# ─── HANDLER REGISTRATION (called from bot.py) ────────────────────────────────

def register_chapter_handlers(application) -> None:
    """Register all chapter-related callback handlers."""
    print("[chapters] Registering chapter handlers...")

    application.add_handler(
        CallbackQueryHandler(handle_generate_chapter, pattern=r"^gen_chapter_\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_ch4_has_data, pattern="^ch4_has_data$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_ch4_gen_questionnaire, pattern="^ch4_gen_questionnaire$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_ch4_gen_template, pattern="^ch4_gen_template$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_ch4_explain_survey, pattern="^ch4_explain_survey$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_download_pdf, pattern="^download_pdf$")
    )

    # Chapter 4 data input — text message when awaiting_ch4_data is set
    from telegram.ext import MessageHandler, filters
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_ch4_data_input,
        ),
        group=1,
    )

    print("[chapters] Chapter handlers registered.")


print("[chapters.py] Chapters handler loaded.")