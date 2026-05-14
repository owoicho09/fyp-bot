print("[onboarding.py] Loading onboarding handler...")

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from services.supabase_service import (
    get_or_create_user, update_user, get_active_project,
    create_project, upsert_session, clear_session,
)
from services.claude_service import run_intake_agent
from services.whisper_service import (
    transcribe_voice_message,
    build_voice_received_message,
    build_transcription_preview,
)
from utils.keyboards import (
    level_keyboard, faculty_keyboard,
    confirm_brief_keyboard, resume_keyboard,
    skip_keyboard, citation_year_keyboard,
)
from utils.helpers import (
    format_project_brief, extract_brief_from_context,
    is_topic_too_short, looks_like_question,
)
from utils.prompts.intake_agent import (
    get_intake_welcome_message,
    get_returning_user_message,
    get_voice_note_processing_message,
    get_voice_note_error_message,
    get_brief_complete_transition,
    get_brief_confirmation_message,
    get_topic_opening_message,
    get_department_prompt_message,
    get_university_prompt_message,
    get_faculty_prompt_message,
    get_topic_too_short_message,
    get_topic_looks_like_question_message,
)
from utils.constants import (
    ASK_LEVEL, ASK_FACULTY, ASK_DEPARTMENT, ASK_UNIVERSITY,
    ASK_TOPIC_OPEN, ASK_FOLLOWUP_1, CONFIRM_BRIEF,
    DISCLAIMER_FACULTIES,
)

# Extra onboarding states
ASK_CHAPTER_FORMAT  = 30
ASK_CITATION_YEAR   = 31


# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(f"[onboarding] /start from user {update.effective_user.id}")
    user = update.effective_user

    try:
        get_or_create_user(
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
        )
    except Exception as e:
        print(f"[onboarding] get_or_create_user error: {e}")

    context.user_data.clear()
    context.user_data["conversation_history"] = []
    context.user_data["onboarding_complete"]  = False

    try:
        existing = get_active_project(user.id)
    except Exception as e:
        print(f"[onboarding] get_active_project error: {e}")
        existing = None

    if existing and existing.get("chapters_completed", 0) > 0:
        print(f"[onboarding] Returning user {user.id} — {existing['chapters_completed']} chapters done")
        context.user_data["onboarding_complete"] = True
        await update.message.reply_text(
            get_returning_user_message(
                user.first_name,
                existing["topic"],
                existing["chapters_completed"],
            ),
            parse_mode="Markdown",
            reply_markup=resume_keyboard(existing["chapters_completed"]),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        get_intake_welcome_message(user.first_name),
        parse_mode="Markdown",
        reply_markup=level_keyboard(),
    )
    return ASK_LEVEL


# ─── STEP 1: Level ────────────────────────────────────────────────────────────

async def handle_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query   = update.callback_query
    await query.answer()
    level   = query.data.replace("level_", "")
    user_id = query.from_user.id
    print(f"[onboarding] Level: {level} | user={user_id}")

    context.user_data["academic_level"] = level
    try:
        update_user(user_id, {"academic_level": level})
    except Exception as e:
        print(f"[onboarding] update_user level error: {e}")

    await query.edit_message_text(
        get_faculty_prompt_message(),
        parse_mode="Markdown",
        reply_markup=faculty_keyboard(),
    )
    return ASK_FACULTY


# ─── STEP 2: Faculty ─────────────────────────────────────────────────────────

async def handle_faculty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query   = update.callback_query
    await query.answer()
    faculty = query.data.replace("faculty_", "")
    user_id = query.from_user.id
    print(f"[onboarding] Faculty: {faculty} | user={user_id}")

    context.user_data["faculty"] = faculty

    if faculty in DISCLAIMER_FACULTIES:
        await query.message.reply_text(
            DISCLAIMER_FACULTIES[faculty],
            parse_mode="Markdown",
        )

    await query.edit_message_text(
        get_department_prompt_message(faculty),
        parse_mode="Markdown",
    )
    return ASK_DEPARTMENT


# ─── STEP 3: Department ───────────────────────────────────────────────────────

async def handle_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dept    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Department: '{dept[:60]}' | user={user_id}")

    if not dept:
        await update.message.reply_text("Please type your department name:")
        return ASK_DEPARTMENT

    context.user_data["department"] = dept
    try:
        update_user(user_id, {"department": dept})
    except Exception as e:
        print(f"[onboarding] update_user department error: {e}")

    await update.message.reply_text(
        get_university_prompt_message(),
        parse_mode="Markdown",
    )
    return ASK_UNIVERSITY


# ─── STEP 4: University ───────────────────────────────────────────────────────

async def handle_university(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    university = update.message.text.strip()
    user_id    = update.effective_user.id
    print(f"[onboarding] University: '{university}' | user={user_id}")

    if not university:
        await update.message.reply_text("Please type your university name:")
        return ASK_UNIVERSITY

    context.user_data["university"] = university
    try:
        update_user(user_id, {"university": university})
    except Exception as e:
        print(f"[onboarding] update_user university error: {e}")

    # Ask citation year range
    await update.message.reply_text(
        "📚 *Citation year range*\n\n"
        "What year range should your references cover?\n\n"
        "By default I use the *last 5 years* which most supervisors prefer "
        "for current and relevant literature.\n\n"
        "Choose below or type a custom range like _2015–2025_:",
        parse_mode="Markdown",
        reply_markup=citation_year_keyboard(),
    )
    return ASK_CITATION_YEAR


# ─── STEP 5: Citation year range ─────────────────────────────────────────────

async def handle_citation_year_button(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Student tapped one of the preset citation year buttons."""
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data    = query.data  # e.g. "cite_year_2019" or "cite_year_any"
    print(f"[onboarding] Citation year button: {data} | user={user_id}")

    if data == "cite_year_any":
        year_from = 1990
    else:
        try:
            year_from = int(data.replace("cite_year_", ""))
        except ValueError:
            year_from = 2019

    context.user_data["citation_year_from"] = year_from
    print(f"[onboarding] Citation year from: {year_from}")

    await query.edit_message_text(
        f"✅ Citations from *{year_from if year_from > 1990 else 'any year'}* onwards.\n\n"
        "Now, does your department or university specify *exact chapter headings* "
        "or section names for your project format?\n\n"
        "For example:\n"
        "• _'Materials and Methods'_ instead of _'Research Methodology'_\n"
        "• _'Results and Interpretation'_ instead of _'Data Presentation'_\n\n"
        "Paste your school's format below, or tap *Skip* if you are not sure:",
        parse_mode="Markdown",
        reply_markup=skip_keyboard("skip_chapter_format"),
    )
    return ASK_CHAPTER_FORMAT


async def handle_citation_year_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Student typed a custom citation year range like '2015-2025'."""
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Citation year text: '{text}' | user={user_id}")

    # Extract the earliest year from whatever they typed
    import re
    years = re.findall(r"\b(19|20)\d{2}\b", text)
    if years:
        year_from = int(min(years))
    elif "any" in text.lower() or "all" in text.lower():
        year_from = 1990
    else:
        year_from = 2019  # default

    context.user_data["citation_year_from"] = year_from
    print(f"[onboarding] Citation year from text: {year_from}")

    await update.message.reply_text(
        f"✅ Citations from *{year_from if year_from > 1990 else 'any year'}* onwards.\n\n"
        "Now, does your department or university specify *exact chapter headings* "
        "or section names for your project format?\n\n"
        "Paste your school's format below, or tap *Skip*:",
        parse_mode="Markdown",
        reply_markup=skip_keyboard("skip_chapter_format"),
    )
    return ASK_CHAPTER_FORMAT


# ─── STEP 6: Chapter format (optional) ───────────────────────────────────────

async def handle_chapter_format_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Chapter format: '{text[:100]}' | user={user_id}")

    if text.lower() not in ("skip", "s", "no", "none", ""):
        context.user_data["chapter_format"] = text
        print(f"[onboarding] Chapter format saved.")

    await update.message.reply_text(
        get_topic_opening_message(),
        parse_mode="Markdown",
    )
    return ASK_TOPIC_OPEN


async def handle_chapter_format_skip(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    print(f"[onboarding] Chapter format skipped | user={query.from_user.id}")

    await query.message.reply_text(
        get_topic_opening_message(),
        parse_mode="Markdown",
    )
    return ASK_TOPIC_OPEN


# ─── STEP 7: Topic (text or voice) ───────────────────────────────────────────

async def handle_topic_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Topic text: '{text[:80]}' | user={user_id}")

    if not text:
        await update.message.reply_text(
            "Please tell me your topic. You can type or send a 🎙️ voice note."
        )
        return ASK_TOPIC_OPEN

    if is_topic_too_short(text):
        await update.message.reply_text(
            get_topic_too_short_message(), parse_mode="Markdown"
        )
        return ASK_TOPIC_OPEN

    if looks_like_question(text):
        await update.message.reply_text(
            get_topic_looks_like_question_message(), parse_mode="Markdown"
        )
        return ASK_TOPIC_OPEN

    return await _process_topic(update, context, text)


async def handle_topic_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    voice   = update.message.voice
    user_id = update.effective_user.id
    print(f"[onboarding] Topic voice: {voice.duration}s | user={user_id}")

    processing_msg = await update.message.reply_text(
        get_voice_note_processing_message()
    )

    try:
        result = await transcribe_voice_message(
            bot=context.bot, file_id=voice.file_id
        )
    except Exception as e:
        print(f"[onboarding] voice error: {e}")
        await processing_msg.edit_text(get_voice_note_error_message())
        return ASK_TOPIC_OPEN

    if not result["success"]:
        await processing_msg.edit_text(get_voice_note_error_message())
        return ASK_TOPIC_OPEN

    transcript = result["transcript"]
    await processing_msg.edit_text(
        build_transcription_preview(transcript),
        parse_mode="Markdown",
    )
    return await _process_topic(update, context, transcript)


async def _process_topic(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> int:
    user_id = update.effective_user.id
    print(f"[onboarding] _process_topic: '{text[:80]}'")

    history = context.user_data.get("conversation_history", [])
    history.append({"role": "user", "content": text})

    student_context = {
        "academic_level": context.user_data.get("academic_level", ""),
        "faculty":        context.user_data.get("faculty", ""),
        "department":     context.user_data.get("department", ""),
        "university":     context.user_data.get("university", ""),
        "chapter_format": context.user_data.get("chapter_format", ""),
    }

    try:
        result = await run_intake_agent(history, student_context)
    except Exception as e:
        print(f"[onboarding] run_intake_agent error: {e}")
        context.user_data["topic"] = text
        return await _show_brief(update, context)

    extracted = result.get("extracted", {})
    for key, value in extracted.items():
        if value is not None and value != "":
            context.user_data[key] = value
            print(f"[onboarding] Extracted: {key} = {str(value)[:60]}")

    if not context.user_data.get("topic"):
        context.user_data["topic"] = text

    reply = result.get("reply", "")
    history.append({"role": "assistant", "content": reply})
    context.user_data["conversation_history"] = history

    if result.get("brief_complete"):
        print(f"[onboarding] Brief complete — going to confirmation")
        return await _show_brief(update, context)

    if reply:
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=skip_keyboard("skip_followup"),
        )
        return ASK_FOLLOWUP_1

    return await _show_brief(update, context)


# ─── STEP 8: ONE follow-up ────────────────────────────────────────────────────

async def handle_followup_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Followup: '{text[:80]}' | user={user_id}")

    if text.lower() in ("skip", "s"):
        return await _show_brief(update, context)

    return await _process_followup(update, context, text)


async def handle_followup_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    voice   = update.message.voice
    user_id = update.effective_user.id
    print(f"[onboarding] Followup voice: {voice.duration}s | user={user_id}")

    processing_msg = await update.message.reply_text(
        get_voice_note_processing_message()
    )

    try:
        result = await transcribe_voice_message(
            bot=context.bot, file_id=voice.file_id
        )
    except Exception as e:
        print(f"[onboarding] followup voice error: {e}")
        await processing_msg.edit_text(get_voice_note_error_message())
        return await _show_brief(update, context)

    if not result["success"]:
        await processing_msg.edit_text(get_voice_note_error_message())
        return await _show_brief(update, context)

    transcript = result["transcript"]
    await processing_msg.edit_text(
        build_transcription_preview(transcript),
        parse_mode="Markdown",
    )
    return await _process_followup(update, context, transcript)


async def handle_followup_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    print(f"[onboarding] Followup skipped")
    return await _show_brief(update, context, message=query.message)


async def _process_followup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> int:
    user_id = update.effective_user.id
    print(f"[onboarding] _process_followup: '{text[:80]}'")

    history = context.user_data.get("conversation_history", [])
    history.append({"role": "user", "content": text})

    student_context = {k: context.user_data.get(k, "") for k in [
        "academic_level", "faculty", "department", "university",
        "topic", "research_question", "population", "time_frame",
        "chapter_format",
    ]}

    try:
        result = await run_intake_agent(history, student_context)
        for key, value in result.get("extracted", {}).items():
            if value is not None and value != "":
                context.user_data[key] = value
                print(f"[onboarding] Followup extracted: {key} = {str(value)[:60]}")
        history.append({"role": "assistant", "content": result.get("reply", "")})
        context.user_data["conversation_history"] = history
    except Exception as e:
        print(f"[onboarding] _process_followup error: {e}")

    return await _show_brief(update, context)


# ─── BRIEF CONFIRMATION ───────────────────────────────────────────────────────

async def _show_brief(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message=None,
) -> int:
    print("[onboarding] _show_brief")
    user_id    = update.effective_user.id if update.effective_user else None
    msg_target = message or update.message

    brief      = extract_brief_from_context(context.user_data)
    brief_card = format_project_brief(brief)

    await msg_target.reply_text(
        get_brief_complete_transition(),
        parse_mode="Markdown",
    )
    await msg_target.reply_text(
        get_brief_confirmation_message(brief_card),
        parse_mode="Markdown",
        reply_markup=confirm_brief_keyboard(),
    )

    if user_id:
        try:
            upsert_session(user_id, "brief_confirmed", brief)
        except Exception as e:
            print(f"[onboarding] upsert_session error: {e}")

    print(f"[onboarding] Brief shown to user {user_id}")
    return CONFIRM_BRIEF


# ─── CONFIRM & GENERATE ───────────────────────────────────────────────────────

async def handle_confirm_brief(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query   = update.callback_query
    await query.answer()
    action  = query.data
    user_id = query.from_user.id
    print(f"[onboarding] Confirm brief: {action} | user={user_id}")

    if action == "change_topic":
        context.user_data.pop("topic", None)
        context.user_data.pop("research_question", None)
        await query.edit_message_text(
            "No problem. Type your revised topic or send a 🎙️ voice note:"
        )
        return ASK_TOPIC_OPEN

    if action == "restart":
        context.user_data.clear()
        try:
            clear_session(user_id)
        except Exception as e:
            print(f"[onboarding] clear_session error: {e}")
        await query.edit_message_text("Starting fresh. Send /start to begin.")
        return ConversationHandler.END

    if action == "gen_chapter_1":
        brief = extract_brief_from_context(context.user_data)

        try:
            create_project(user_id, brief)
        except Exception as e:
            print(f"[onboarding] create_project error: {e}")
            await query.message.reply_text(
                "Something went wrong saving your project. "
                "Please send /start and try again."
            )
            return ConversationHandler.END

        context.user_data["onboarding_complete"]  = True
        context.user_data["conversation_history"] = []
        print(f"[onboarding] Project created for {user_id}.")

        await query.edit_message_text(
            "✅ Project saved. Generating *Chapter 1: Introduction* now...\n\n"
            "This takes 30–60 seconds. Please wait ⏳",
            parse_mode="Markdown",
        )

        try:
            from handlers.chapters import generate_chapter_1
            await generate_chapter_1(query, context)
        except Exception as e:
            print(f"[onboarding] generate_chapter_1 error: {e}")
            await query.message.reply_text(
                "Chapter 1 generation failed. Send /start — "
                "your project is saved, tap Continue to retry."
            )

        return ConversationHandler.END

    return CONFIRM_BRIEF


# ─── CONVERSATION HANDLER ─────────────────────────────────────────────────────

def get_onboarding_handler() -> ConversationHandler:
    print("[onboarding] Registering ConversationHandler...")
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_LEVEL: [
                CallbackQueryHandler(handle_level, pattern="^level_"),
            ],
            ASK_FACULTY: [
                CallbackQueryHandler(handle_faculty, pattern="^faculty_"),
            ],
            ASK_DEPARTMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_department),
            ],
            ASK_UNIVERSITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_university),
            ],
            ASK_CITATION_YEAR: [
                CallbackQueryHandler(handle_citation_year_button, pattern="^cite_year_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_citation_year_text),
            ],
            ASK_CHAPTER_FORMAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chapter_format_text),
                CallbackQueryHandler(handle_chapter_format_skip, pattern="^skip_chapter_format$"),
            ],
            ASK_TOPIC_OPEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic_text),
                MessageHandler(filters.VOICE, handle_topic_voice),
            ],
            ASK_FOLLOWUP_1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_followup_text),
                MessageHandler(filters.VOICE, handle_followup_voice),
                CallbackQueryHandler(handle_followup_skip, pattern="^skip_followup$"),
            ],
            CONFIRM_BRIEF: [
                CallbackQueryHandler(
                    handle_confirm_brief,
                    pattern="^(gen_chapter_1|change_topic|restart)$",
                ),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(handle_confirm_brief, pattern="^restart$"),
        ],
        allow_reentry=True,
        name="onboarding",
        persistent=False,
    )


print("[onboarding.py] Onboarding handler loaded.")