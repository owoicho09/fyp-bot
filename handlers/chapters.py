print("[chapters.py] Loading chapters handler...")

import json
import re
from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, MessageHandler, filters,
)
from services.supabase_service import (
    get_active_project, save_chapter_content, update_project,
    add_verified_reference, is_subscribed, get_user,
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
    chapter_outline_keyboard,
)
from utils.prompts.intake_agent import (
    get_generating_message, get_chapter_2_citation_update,
    get_error_message,
)
from utils.constants import CHAPTER_NAMES, FREE_CHAPTERS, PAID_CHAPTERS


# ─── ENTRY POINT FROM ONBOARDING ─────────────────────────────────────────────

async def generate_chapter_1(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called directly from onboarding after brief is confirmed."""
    print(f"[chapters] generate_chapter_1 from onboarding")
    user_id = query.from_user.id
    # Chapter 1 from onboarding skips the outline prompt — goes straight to generation
    await _generate_and_deliver_chapter(
        user_id=user_id,
        chapter_number=1,
        context=context,
        send_target=query.message,
    )


# ─── CALLBACK: gen_chapter_N ─────────────────────────────────────────────────

async def handle_generate_chapter(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    match = re.match(r"^gen_chapter_(\d+)$", query.data)
    if not match:
        print(f"[chapters] Invalid callback: {query.data}")
        return

    chapter_number = int(match.group(1))
    print(f"[chapters] gen_chapter_{chapter_number}: user={user_id}")

    # Paywall
    if chapter_number in PAID_CHAPTERS:
        if not is_subscribed(user_id):
            print(f"[chapters] Paywall ch{chapter_number} user={user_id}")
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
            print(f"[chapters] Ch4 data gate user={user_id}")
            await query.message.reply_text(
                "📊 *Before I write Chapter 4, I need your data.*\n\n"
                "Chapter 4 presents your actual research findings. "
                "I will never fabricate data.\n\n"
                "What would you like to do?",
                parse_mode="Markdown",
                reply_markup=chapter_4_gate_keyboard(),
            )
            return

    # Offer outline option — only once per chapter
    outline_key = f"outline_offered_{chapter_number}"
    if not context.user_data.get(outline_key):
        context.user_data[outline_key] = True
        ch_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            f"📖 *Chapter {chapter_number}: {ch_name}*\n\n"
            f"Do you have a specific outline or instructions you want me to follow "
            f"for this chapter?\n\n"
            f"You can drop:\n"
            f"• Your supervisor's chapter outline\n"
            f"• Specific section headings your school requires\n"
            f"• Any particular angle or focus for this chapter\n\n"
            f"Or just generate with the standard format:",
            parse_mode="Markdown",
            reply_markup=chapter_outline_keyboard(chapter_number),
        )
        return

    # Outline already offered — proceed to generation
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _generate_and_deliver_chapter(
        user_id=user_id,
        chapter_number=chapter_number,
        context=context,
        send_target=query.message,
    )


# ─── OUTLINE HANDLERS ─────────────────────────────────────────────────────────

async def handle_has_outline(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Student tapped 'I have an outline'."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    match = re.match(r"^has_outline_(\d+)$", query.data)
    if not match:
        return

    chapter_number = int(match.group(1))
    print(f"[chapters] has_outline ch{chapter_number} user={user_id}")

    context.user_data["awaiting_outline_chapter"] = chapter_number
    ch_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")

    await query.edit_message_text(
        f"📝 *Your outline for Chapter {chapter_number}: {ch_name}*\n\n"
        f"Paste your outline or specific instructions now.\n\n"
        f"Examples:\n"
        f"• Your supervisor's exact chapter structure\n"
        f"• Section headings your school requires\n"
        f"• 'Focus on X, include Y, use Z approach'\n\n"
        f"Send it now (text or 🎙️ voice note):",
        parse_mode="Markdown",
    )


async def handle_no_outline(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Student tapped 'Generate with standard format'."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    match = re.match(r"^no_outline_(\d+)$", query.data)
    if not match:
        return

    chapter_number = int(match.group(1))
    print(f"[chapters] no_outline ch{chapter_number} user={user_id}")

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    await _generate_and_deliver_chapter(
        user_id=user_id,
        chapter_number=chapter_number,
        context=context,
        send_target=query.message,
    )


async def handle_outline_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Receive student's typed outline then generate."""
    chapter_number = context.user_data.get("awaiting_outline_chapter")
    if not chapter_number:
        return

    user_id      = update.effective_user.id
    outline_text = update.message.text.strip()
    print(f"[chapters] Outline input ch{chapter_number} user={user_id}: {len(outline_text)} chars")

    if len(outline_text) < 5:
        await update.message.reply_text(
            "That outline seems too short. Please paste your actual outline or instructions:"
        )
        return

    # Save to Supabase
    try:
        update_project(user_id, {f"chapter_{chapter_number}_outline": outline_text})
        print(f"[chapters] Outline saved ch{chapter_number}")
    except Exception as e:
        print(f"[chapters] Outline save error: {e}")

    context.user_data.pop("awaiting_outline_chapter", None)

    ch_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")
    await update.message.reply_text(
        f"✅ *Outline received.* Generating *Chapter {chapter_number}: {ch_name}* "
        f"following your structure...\n\nPlease wait ⏳",
        parse_mode="Markdown",
    )

    await _generate_and_deliver_chapter(
        user_id=user_id,
        chapter_number=chapter_number,
        context=context,
        send_target=update.message,
    )


async def handle_outline_voice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Receive student's voice outline then generate."""
    chapter_number = context.user_data.get("awaiting_outline_chapter")
    if not chapter_number:
        return

    user_id = update.effective_user.id
    voice   = update.message.voice
    print(f"[chapters] Outline voice ch{chapter_number} user={user_id}: {voice.duration}s")

    from services.whisper_service import transcribe_voice_message, build_voice_received_message
    processing_msg = await update.message.reply_text(build_voice_received_message(voice.duration))

    try:
        result = await transcribe_voice_message(bot=update.get_bot(), file_id=voice.file_id)
    except Exception as e:
        print(f"[chapters] Outline voice transcription error: {e}")
        await processing_msg.edit_text("Could not transcribe. Please type your outline instead.")
        return

    if not result["success"]:
        await processing_msg.edit_text("Could not transcribe. Please type your outline instead.")
        return

    outline_text = result["transcript"]
    await processing_msg.edit_text(f"🎙️ Got it: _{outline_text[:200]}_", parse_mode="Markdown")

    # Save to Supabase
    try:
        update_project(user_id, {f"chapter_{chapter_number}_outline": outline_text})
    except Exception as e:
        print(f"[chapters] Outline voice save error: {e}")

    context.user_data.pop("awaiting_outline_chapter", None)

    ch_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")
    await update.message.reply_text(
        f"✅ *Outline received.* Generating *Chapter {chapter_number}: {ch_name}* "
        f"following your structure...\n\nPlease wait ⏳",
        parse_mode="Markdown",
    )

    await _generate_and_deliver_chapter(
        user_id=user_id,
        chapter_number=chapter_number,
        context=context,
        send_target=update.message,
    )


# ─── CORE GENERATION ──────────────────────────────────────────────────────────

async def _generate_and_deliver_chapter(
    user_id: int,
    chapter_number: int,
    context: ContextTypes.DEFAULT_TYPE,
    send_target,
) -> None:
    print(f"[chapters] _generate_and_deliver_chapter: user={user_id} ch={chapter_number}")
    chapter_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")

    project = get_active_project(user_id)
    if not project:
        await send_target.reply_text(
            "I could not find your active project. Please send /start."
        )
        return

    user  = get_user(user_id)
    brief = _project_to_brief(project, user)

    status_msg = await send_target.reply_text(
        get_generating_message(chapter_number, chapter_name),
        parse_mode="Markdown",
    )

    # Live Nigerian stats
    live_stats = {}
    try:
        print(f"[chapters] Fetching Nigerian stats ch{chapter_number}...")
        live_stats = await search_nigerian_stats(brief.get("topic", ""))
        print(f"[chapters] Stats: {len(live_stats)} indicators")
    except Exception as e:
        print(f"[chapters] Stats fetch error (non-fatal): {e}")

    # Citation pipeline (Chapter 2 only)
    citations = []
    if chapter_number == 2:
        citations = await _run_citation_pipeline(
            brief=brief,
            status_msg=status_msg,
            user_id=user_id,
            year_from=brief.get("citation_year_from", 2019),
        )

    # Previous chapters for consistency
    previous_chapters = _load_previous_chapters(project, chapter_number)

    # Generate
    try:
        await status_msg.edit_text(
            f"✍️ Writing Chapter {chapter_number}: {chapter_name}..."
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
            get_error_message(f"generating Chapter {chapter_number}")
        )
        return

    # Extract objectives from Chapter 1
    if chapter_number == 1:
        _extract_and_save_chapter_1_data(user_id, content)
        content = _strip_extracted_data_block(content)

    # Project complete marker
    is_complete = "<!--PROJECT_COMPLETE-->" in content
    if is_complete:
        content = content.replace("<!--PROJECT_COMPLETE-->", "").strip()

    # Save
    save_chapter_content(user_id, chapter_number, content)
    print(f"[chapters] Chapter {chapter_number} saved.")

    try:
        await status_msg.delete()
    except Exception:
        pass

    # Deliver
    await send_target.reply_text(
        format_chapter_intro(chapter_number, brief.get("topic", "")),
        parse_mode="Markdown",
    )

    await send_long_message(
        bot=context.bot,
        chat_id=send_target.chat_id,
        text=content,
        parse_mode="Markdown",
    )

    await send_target.reply_text(
        format_chapter_disclaimer(),
        parse_mode="Markdown",
    )

    # Next step
    if is_complete or chapter_number == 5:
        await send_target.reply_text(
            format_completion_message(brief.get("topic", "")),
            parse_mode="Markdown",
            reply_markup=download_pdf_keyboard(),
        )
    elif chapter_number == 2 and not is_subscribed(user_id):
        await send_target.reply_text(
            format_paywall_message(),
            parse_mode="Markdown",
            reply_markup=payment_plans_keyboard(),
        )
    else:
        next_ch = chapter_number + 1
        await send_target.reply_text(
            f"✅ *Chapter {chapter_number}* is ready!\n\n"
            f"Tap below when you're ready for the next chapter.",
            parse_mode="Markdown",
            reply_markup=next_chapter_keyboard(next_ch),
        )

    print(f"[chapters] Chapter {chapter_number} delivered to user {user_id}")


# ─── CITATION PIPELINE ────────────────────────────────────────────────────────

async def _run_citation_pipeline(
    brief: dict,
    status_msg,
    user_id: int,
    year_from: int = 2019,
) -> list[dict]:
    print(f"[chapters] Citation pipeline user={user_id} year_from={year_from}")
    try:
        await status_msg.edit_text(
            "🔍 Generating search queries for your literature review..."
        )
        queries = await generate_citation_queries(brief)
        print(f"[chapters] {len(queries)} citation queries generated")

        await status_msg.edit_text(
            f"📚 Searching academic databases for verified citations "
            f"({'from ' + str(year_from) if year_from > 1990 else 'all years'})..."
        )
        papers = await find_citations_batch(
            queries,
            max_per_query=5,
            year_from=year_from,
        )
        print(f"[chapters] {len(papers)} unique papers found")

        for paper in papers:
            add_verified_reference(user_id, paper)

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


# ─── CHAPTER 4 DATA GATE ──────────────────────────────────────────────────────

async def handle_ch4_has_data(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"[chapters] ch4_has_data user={user_id}")

    await query.edit_message_text(
        "Great! Please send me your data now.\n\n"
        "You can paste:\n"
        "• A table (copy from Excel/Google Sheets)\n"
        "• A summary of your responses (e.g. '120 respondents, 65% female...')\n"
        "• Raw frequency counts per question\n\n"
        "The more detail, the better the analysis:"
    )
    context.user_data["awaiting_ch4_data"] = True


async def handle_ch4_data_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not context.user_data.get("awaiting_ch4_data"):
        return

    user_id   = update.effective_user.id
    data_text = update.message.text.strip()
    print(f"[chapters] Ch4 data from {user_id}: {len(data_text)} chars")

    if len(data_text) < 20:
        await update.message.reply_text(
            "That does not look like enough data. "
            "Please paste your actual survey results or response summary."
        )
        return

    update_project(user_id, {"student_data": data_text})
    context.user_data.pop("awaiting_ch4_data", None)

    await update.message.reply_text(
        "✅ Data received. Generating *Chapter 4* now...\n\nPlease wait ⏳",
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
    print(f"[chapters] ch4_gen_questionnaire user={user_id}")

    await query.edit_message_text("Generating your research questionnaire... ⏳")

    project = get_active_project(user_id)
    if not project:
        await query.message.reply_text("Could not find your project. Send /start.")
        return

    user  = get_user(user_id)
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
                "_Administer this to your respondents, collect responses, "
                "then come back and share your data to generate Chapter 4._"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[chapters] Questionnaire error: {e}")
        await query.message.reply_text(get_error_message("generating the questionnaire"))


async def handle_ch4_gen_template(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    print(f"[chapters] ch4_gen_template user={query.from_user.id}")

    template = (
        "📊 *Data Entry Template*\n\n"
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
    print(f"[chapters] ch4_explain_survey user={query.from_user.id}")

    explanation = (
        "📖 *How to Administer Your Survey*\n\n"
        "*Step 1 — Print or share digitally*\n"
        "Print copies or create a Google Form. Google Forms is free and easy to share via WhatsApp.\n\n"
        "*Step 2 — Reach your sample*\n"
        "Go to your study location and distribute to your target respondents.\n\n"
        "*Step 3 — Collect responses*\n"
        "Collect immediately if paper-based, or set a 3–5 day deadline for Google Forms.\n\n"
        "*Step 4 — Count your responses*\n"
        "For each question, count how many chose each option. "
        "Enter the counts into the data template.\n\n"
        "*Step 5 — Come back with your data*\n"
        "Return here and I'll analyse everything and write Chapter 4.\n\n"
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
    print(f"[chapters] handle_download_pdf user={user_id}")

    await query.message.reply_text("Generating your Word document... ⏳")

    project = get_active_project(user_id)
    if not project:
        await query.message.reply_text("Could not find your project. Send /start.")
        return

    try:
        from services.docx_service import generate_project_docx

        user = get_user(user_id)
        if user:
            project["university"]     = project.get("university")     or user.get("university", "")
            project["department"]     = project.get("department")     or user.get("department", "")
            project["academic_level"] = project.get("academic_level") or user.get("academic_level", "bsc")
            project["faculty"]        = project.get("faculty")        or user.get("faculty", "")

        docx_buffer   = generate_project_docx(project, user)
        chapters_done = project.get("chapters_completed", 0)
        topic_slug    = project.get("topic", "project")[:30].replace(" ", "_")
        filename      = f"FYP_Mentor_{topic_slug}_Ch1-{chapters_done}.docx"

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=docx_buffer,
            filename=filename,
            caption=(
                f"📄 *Your project Word document* — Chapters 1–{chapters_done}\n\n"
                "Open in Microsoft Word or Google Docs to edit. "
                "Read through, add your own voice, and review with your supervisor "
                "before submission."
            ),
            parse_mode="Markdown",
        )
        print(f"[chapters] DOCX sent to user {user_id}")

    except Exception as e:
        print(f"[chapters] DOCX error: {e}")
        await query.message.reply_text(
            "Document generation failed. Your chapters are saved — try again in a moment."
        )

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _project_to_brief(project: dict, user: dict = None) -> dict:
    print(f"[chapters] _project_to_brief project_id={project.get('id')}")
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
        "topic":              project.get("topic", ""),
        "research_question":  project.get("research_question", ""),
        "population":         project.get("population", ""),
        "time_frame":         project.get("time_frame", ""),
        "research_type":      project.get("research_type")      or u.get("research_type", "quantitative"),
        "citation_style":     project.get("citation_style")     or u.get("citation_style", "apa7"),
        "citation_year_from": project.get("citation_year_from") or 2019,
        "objectives":         _parse("objectives"),
        "hypotheses":         _parse("hypotheses"),
        "turnitin":           project.get("turnitin", False),
        "supervisor_context": project.get("supervisor_context", "") or u.get("supervisor_context", ""),
        "nigerian_context":   project.get("nigerian_context", ""),
        "student_background": project.get("student_background", ""),
        "student_data":       project.get("student_data", ""),
        "department":         project.get("department")         or u.get("department", ""),
        "university":         project.get("university")         or u.get("university", ""),
        "academic_level":     project.get("academic_level")     or u.get("academic_level", "bsc"),
        "faculty":            project.get("faculty")            or u.get("faculty", ""),
        "chapter_format":     project.get("chapter_format", ""),
        "chapter_1_outline":  project.get("chapter_1_outline", ""),
        "chapter_2_outline":  project.get("chapter_2_outline", ""),
        "chapter_3_outline":  project.get("chapter_3_outline", ""),
        "chapter_4_outline":  project.get("chapter_4_outline", ""),
        "chapter_5_outline":  project.get("chapter_5_outline", ""),
    }


def _load_previous_chapters(project: dict, current_chapter: int) -> dict:
    prev = {}
    for ch in range(1, current_chapter):
        content = project.get(f"chapter_{ch}_content", "")
        if content:
            prev[ch] = content
    print(f"[chapters] Loaded {len(prev)} previous chapters")
    return prev


def _extract_and_save_chapter_1_data(user_id: int, content: str) -> None:
    print(f"[chapters] _extract_and_save_chapter_1_data user={user_id}")
    try:
        match = re.search(
            r"<!--EXTRACTED_DATA\s*(.*?)\s*EXTRACTED_DATA-->",
            content, re.DOTALL,
        )
        if not match:
            print("[chapters] No EXTRACTED_DATA block in Chapter 1")
            return
        data       = json.loads(match.group(1))
        objectives = data.get("objectives", [])
        questions  = data.get("research_questions", [])
        hypotheses = data.get("hypotheses", [])
        update_project(user_id, {
            "objectives":         json.dumps(objectives),
            "research_questions": json.dumps(questions),
            "hypotheses":         json.dumps(hypotheses),
        })
        print(
            f"[chapters] Ch1 data saved: "
            f"{len(objectives)} objectives, "
            f"{len(questions)} questions, "
            f"{len(hypotheses)} hypotheses"
        )
    except Exception as e:
        print(f"[chapters] _extract_and_save_chapter_1_data error: {e}")


def _strip_extracted_data_block(content: str) -> str:
    return re.sub(
        r"<!--EXTRACTED_DATA.*?EXTRACTED_DATA-->",
        "", content, flags=re.DOTALL,
    ).strip()


# ─── HANDLER REGISTRATION ─────────────────────────────────────────────────────

def register_chapter_handlers(application) -> None:
    print("[chapters] Registering chapter handlers...")

    application.add_handler(
        CallbackQueryHandler(handle_generate_chapter, pattern=r"^gen_chapter_\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_has_outline, pattern=r"^has_outline_\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_no_outline, pattern=r"^no_outline_\d+$")
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

    # Text input handlers at group 1
    # Each checks its own condition and exits early if not applicable
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_outline_input),
        group=1,
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ch4_data_input),
        group=1,
    )
    application.add_handler(
        MessageHandler(filters.VOICE, handle_outline_voice),
        group=1,
    )

    print("[chapters] Chapter handlers registered.")


print("[chapters.py] Chapters handler loaded.")