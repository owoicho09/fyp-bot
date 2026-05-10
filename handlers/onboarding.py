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
    skip_keyboard,
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

    await update.message.reply_text(
        get_topic_opening_message(),
        parse_mode="Markdown",
    )
    return ASK_TOPIC_OPEN


# ─── STEP 5: Topic (text or voice) ───────────────────────────────────────────

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
        await update.message.reply_text(get_topic_too_short_message(), parse_mode="Markdown")
        return ASK_TOPIC_OPEN

    if looks_like_question(text):
        await update.message.reply_text(get_topic_looks_like_question_message(), parse_mode="Markdown")
        return ASK_TOPIC_OPEN

    return await _process_topic(update, context, text)


async def handle_topic_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    voice   = update.message.voice
    user_id = update.effective_user.id
    print(f"[onboarding] Topic voice: {voice.duration}s | user={user_id}")

    processing_msg = await update.message.reply_text(get_voice_note_processing_message())

    try:
        result = await transcribe_voice_message(bot=context.bot, file_id=voice.file_id)
    except Exception as e:
        print(f"[onboarding] voice error: {e}")
        await processing_msg.edit_text(get_voice_note_error_message())
        return ASK_TOPIC_OPEN

    if not result["success"]:
        await processing_msg.edit_text(get_voice_note_error_message())
        return ASK_TOPIC_OPEN

    transcript = result["transcript"]
    print(f"[onboarding] Transcript: '{transcript[:100]}'")
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
    """
    Run the intake agent on the topic message.
    Claude silently extracts: topic, research_question, population,
    time_frame, research_type, citation_style, nigerian_context.

    If it has enough → go straight to brief confirmation.
    If it needs ONE thing → ask one smart question then confirm.
    No more than one follow-up. Ever.
    """
    user_id = update.effective_user.id
    print(f"[onboarding] _process_topic: '{text[:80]}'")

    history = context.user_data.get("conversation_history", [])
    history.append({"role": "user", "content": text})

    student_context = {
        "academic_level": context.user_data.get("academic_level", ""),
        "faculty":        context.user_data.get("faculty", ""),
        "department":     context.user_data.get("department", ""),
        "university":     context.user_data.get("university", ""),
    }

    try:
        result = await run_intake_agent(history, student_context)
    except Exception as e:
        print(f"[onboarding] run_intake_agent error: {e}")
        # On error — store topic and proceed anyway
        context.user_data["topic"] = text
        return await _show_brief(update, context)

    # Merge extracted fields — never overwrite topic with something different
    extracted = result.get("extracted", {})
    for key, value in extracted.items():
        if value is not None and value != "":
            context.user_data[key] = value
            print(f"[onboarding] Extracted: {key} = {str(value)[:60]}")

    # Always store the raw text as topic if nothing better was extracted
    if not context.user_data.get("topic"):
        context.user_data["topic"] = text

    reply = result.get("reply", "")
    history.append({"role": "assistant", "content": reply})
    context.user_data["conversation_history"] = history

    # Claude says it has enough — go straight to brief
    if result.get("brief_complete"):
        print(f"[onboarding] Brief complete — skipping follow-up")
        return await _show_brief(update, context)

    # Ask ONE follow-up if Claude needs one more piece
    if reply:
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=skip_keyboard("skip_followup"),
        )
        return ASK_FOLLOWUP_1

    # No follow-up needed — go to brief
    return await _show_brief(update, context)


# ─── STEP 6: ONE follow-up ────────────────────────────────────────────────────

async def handle_followup_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Followup text: '{text[:80]}' | user={user_id}")

    if text.lower() in ("skip", "s"):
        return await _show_brief(update, context)

    return await _process_followup(update, context, text)


async def handle_followup_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    voice   = update.message.voice
    user_id = update.effective_user.id
    print(f"[onboarding] Followup voice: {voice.duration}s | user={user_id}")

    processing_msg = await update.message.reply_text(get_voice_note_processing_message())

    try:
        result = await transcribe_voice_message(bot=context.bot, file_id=voice.file_id)
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
    """
    Process the one follow-up answer.
    Extract anything useful then go straight to brief — no more questions.
    """
    user_id = update.effective_user.id
    print(f"[onboarding] _process_followup: '{text[:80]}'")

    history = context.user_data.get("conversation_history", [])
    history.append({"role": "user", "content": text})

    student_context = {k: context.user_data.get(k, "") for k in [
        "academic_level", "faculty", "department", "university",
        "topic", "research_question", "population", "time_frame",
    ]}

    try:
        result = await run_intake_agent(history, student_context)
        extracted = result.get("extracted", {})
        for key, value in extracted.items():
            if value is not None and value != "":
                context.user_data[key] = value
                print(f"[onboarding] Followup extracted: {key} = {str(value)[:60]}")
        history.append({"role": "assistant", "content": result.get("reply", "")})
        context.user_data["conversation_history"] = history
    except Exception as e:
        print(f"[onboarding] _process_followup error: {e}")

    # Always proceed to brief after one follow-up — no exceptions
    return await _show_brief(update, context)


# ─── BRIEF CONFIRMATION ───────────────────────────────────────────────────────

async def _show_brief(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message=None,
) -> int:
    """
    Show the assembled project brief to the student for confirmation.
    No validation. No rejection. Just show what we have and let them confirm.
    """
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