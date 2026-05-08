print("[onboarding.py] Loading onboarding handler...")

import json
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from services.supabase_service import (
    get_or_create_user, update_user, get_active_project,
    create_project, upsert_session, clear_session,
)
from services.claude_service import (
    run_intake_agent, validate_topic_with_ai,
    recommend_research_design,
)
from services.whisper_service import (
    transcribe_voice_message,
    build_voice_received_message,
    build_transcription_preview,
)
from utils.keyboards import (
    level_keyboard, faculty_keyboard, research_design_keyboard,
    citation_keyboard, turnitin_keyboard, skip_keyboard,
    confirm_brief_keyboard, resume_keyboard,
)
from utils.helpers import (
    format_project_brief, extract_brief_from_context,
    clean_topic, is_topic_too_short, is_topic_too_long,
    looks_like_question, send_long_message,
)
from utils.prompts.intake_agent import (
    get_intake_welcome_message, get_faculty_prompt_message,
    get_department_prompt_message, get_university_prompt_message,
    get_topic_opening_message, get_followup_transition_message,
    get_research_design_prompt_message, get_citation_prompt_message,
    get_turnitin_prompt_message, get_supervisor_prompt_message,
    get_brief_complete_transition, get_brief_confirmation_message,
    get_topic_too_short_message, get_topic_too_long_message,
    get_topic_looks_like_question_message,
    get_validation_failed_message, get_returning_user_message,
    get_voice_note_processing_message, get_voice_note_error_message,
)
from utils.constants import (
    ASK_LEVEL, ASK_FACULTY, ASK_DEPARTMENT, ASK_UNIVERSITY,
    ASK_TOPIC_OPEN, ASK_FOLLOWUP_1, ASK_FOLLOWUP_2, ASK_FOLLOWUP_3,
    ASK_SUPERVISOR, ASK_RESEARCH_DESIGN, ASK_CITATION,
    CONFIRM_BRIEF, AWAIT_CHAPTER_1, DISCLAIMER_FACULTIES,
    MAX_TOPIC_RETRIES,
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

    # Clear all stale context
    context.user_data.clear()
    context.user_data["topic_retry_count"]    = 0
    context.user_data["conversation_history"] = []
    context.user_data["onboarding_complete"]  = False

    # Check for existing active project — offer resume
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

    # New user — begin intake
    await update.message.reply_text(
        get_intake_welcome_message(user.first_name),
        parse_mode="Markdown",
        reply_markup=level_keyboard(),
    )
    return ASK_LEVEL


# ─── STEP 1: Academic level ───────────────────────────────────────────────────

async def handle_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
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


# ─── STEP 3: Department (typed) ───────────────────────────────────────────────

async def handle_department(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
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


# ─── STEP 4: University (typed) ───────────────────────────────────────────────

async def handle_university(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
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


# ─── STEP 5: Topic open (text or voice) ──────────────────────────────────────

async def handle_topic_open_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Topic open (text): '{text[:80]}' | user={user_id}")

    if not text:
        await update.message.reply_text(
            "Please tell me about your topic. You can type or send a voice note."
        )
        return ASK_TOPIC_OPEN

    return await _process_topic_input(update, context, text)


async def handle_topic_open_voice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    voice   = update.message.voice
    user_id = update.effective_user.id
    print(f"[onboarding] Topic open (voice): {voice.duration}s | user={user_id}")

    processing_msg = await update.message.reply_text(
        get_voice_note_processing_message()
    )

    try:
        result = await transcribe_voice_message(
            bot=context.bot,
            file_id=voice.file_id,
        )
    except Exception as e:
        print(f"[onboarding] voice transcription exception: {e}")
        await processing_msg.edit_text(get_voice_note_error_message())
        return ASK_TOPIC_OPEN

    if not result["success"]:
        print(f"[onboarding] Voice transcription failed: {result.get('error')}")
        await processing_msg.edit_text(get_voice_note_error_message())
        return ASK_TOPIC_OPEN

    transcript = result["transcript"]
    print(f"[onboarding] Transcript: '{transcript[:100]}'")

    await processing_msg.edit_text(
        build_transcription_preview(transcript),
        parse_mode="Markdown",
    )
    return await _process_topic_input(update, context, transcript)


async def _process_topic_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> int:
    user_id = update.effective_user.id
    print(f"[onboarding] _process_topic_input: '{text[:80]}'")

    history = context.user_data.get("conversation_history", [])
    history.append({"role": "user", "content": text})

    student_context = {
        "academic_level": context.user_data.get("academic_level", ""),
        "faculty":        context.user_data.get("faculty", ""),
        "department":     context.user_data.get("department", ""),
        "university":     context.user_data.get("university", ""),
    }

    try:
        agent_result = await run_intake_agent(history, student_context)
    except Exception as e:
        print(f"[onboarding] run_intake_agent error: {e}")
        await update.message.reply_text(
            "I had a moment there. Could you tell me about your topic again?"
        )
        return ASK_TOPIC_OPEN

    extracted = agent_result.get("extracted", {})
    for key, value in extracted.items():
        if value is not None and value != "":
            context.user_data[key] = value
            print(f"[onboarding] Extracted: {key}={str(value)[:50]}")

    reply = agent_result.get("reply", "")
    history.append({"role": "assistant", "content": reply})
    context.user_data["conversation_history"] = history

    # Basic topic validation
    topic = context.user_data.get("topic", "")
    if topic:
        if is_topic_too_short(topic):
            await update.message.reply_text(
                get_topic_too_short_message(),
                parse_mode="Markdown",
            )
            return ASK_TOPIC_OPEN

        if looks_like_question(topic):
            await update.message.reply_text(
                get_topic_looks_like_question_message(),
                parse_mode="Markdown",
            )
            return ASK_TOPIC_OPEN

    # Brief complete — move to research design
    if agent_result.get("brief_complete"):
        print(f"[onboarding] Brief complete after topic open.")
        if reply:
            await update.message.reply_text(reply, parse_mode="Markdown")
        return await _ask_research_design(update, context)

    # Continue with follow-ups
    if reply:
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=skip_keyboard("skip_followup_1"),
        )
    return ASK_FOLLOWUP_1


# ─── STEP 6–8: Follow-up questions ───────────────────────────────────────────

async def handle_followup_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: int
) -> int:
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Followup text state={state}: '{text[:80]}' | user={user_id}")

    if text.lower() in ("skip", "s"):
        return await _advance_followup(update, context, state, skipped=True)

    return await _run_followup_agent(update, context, text, state)


async def handle_followup_voice(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: int
) -> int:
    voice   = update.message.voice
    user_id = update.effective_user.id
    print(f"[onboarding] Followup voice state={state}: {voice.duration}s | user={user_id}")

    processing_msg = await update.message.reply_text(get_voice_note_processing_message())

    try:
        result = await transcribe_voice_message(bot=context.bot, file_id=voice.file_id)
    except Exception as e:
        print(f"[onboarding] followup voice error: {e}")
        await processing_msg.edit_text(get_voice_note_error_message())
        return state

    if not result["success"]:
        await processing_msg.edit_text(get_voice_note_error_message())
        return state

    transcript = result["transcript"]
    await processing_msg.edit_text(
        build_transcription_preview(transcript),
        parse_mode="Markdown",
    )
    return await _run_followup_agent(update, context, transcript, state)


async def handle_followup_skip(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: int
) -> int:
    query = update.callback_query
    await query.answer()
    print(f"[onboarding] Followup skipped state={state}")
    return await _advance_followup(update, context, state, skipped=True, query=query)


async def _run_followup_agent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    current_state: int,
) -> int:
    user_id = update.effective_user.id
    print(f"[onboarding] _run_followup_agent state={current_state}: '{text[:60]}'")

    history = context.user_data.get("conversation_history", [])
    history.append({"role": "user", "content": text})

    student_context = {k: context.user_data.get(k, "") for k in [
        "academic_level", "faculty", "department", "university",
        "topic", "research_question", "population", "time_frame",
    ]}

    try:
        agent_result = await run_intake_agent(history, student_context)
    except Exception as e:
        print(f"[onboarding] _run_followup_agent error: {e}")
        await update.message.reply_text(
            "I had a moment. Please try again or type 'skip' to continue."
        )
        return current_state

    extracted = agent_result.get("extracted", {})
    for key, value in extracted.items():
        if value is not None and value != "":
            context.user_data[key] = value

    reply = agent_result.get("reply", "")
    history.append({"role": "assistant", "content": reply})
    context.user_data["conversation_history"] = history

    if agent_result.get("brief_complete"):
        print(f"[onboarding] Brief complete at followup state={current_state}")
        if reply:
            await update.message.reply_text(reply, parse_mode="Markdown")
        return await _ask_research_design(update, context)

    return await _advance_followup(update, context, current_state, reply=reply)


async def _advance_followup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    current_state: int,
    skipped: bool = False,
    reply: str = None,
    query=None,
) -> int:
    next_states = {
        ASK_FOLLOWUP_1: ASK_FOLLOWUP_2,
        ASK_FOLLOWUP_2: ASK_FOLLOWUP_3,
        ASK_FOLLOWUP_3: ASK_SUPERVISOR,
    }
    next_state  = next_states.get(current_state)
    msg_target  = query.message if query else update.message

    if reply and not skipped:
        await msg_target.reply_text(reply, parse_mode="Markdown")

    if next_state == ASK_SUPERVISOR:
        supervisor_msg = get_supervisor_prompt_message()
        if isinstance(supervisor_msg, tuple):
            supervisor_msg = supervisor_msg[0]
        await msg_target.reply_text(
            supervisor_msg,
            parse_mode="Markdown",
            reply_markup=skip_keyboard("skip_supervisor"),
        )
        return ASK_SUPERVISOR

    if next_state:
        history = context.user_data.get("conversation_history", [])
        student_context = {k: context.user_data.get(k, "") for k in [
            "academic_level", "faculty", "department", "university",
            "topic", "research_question", "population", "time_frame",
        ]}
        history.append({
            "role": "user",
            "content": "[SYSTEM: Student skipped — ask the next follow-up question]"
        })

        try:
            agent_result = await run_intake_agent(history, student_context)
        except Exception as e:
            print(f"[onboarding] _advance_followup agent error: {e}")
            return await _ask_research_design(update, context)

        if agent_result.get("brief_complete"):
            return await _ask_research_design(update, context)

        next_reply = agent_result.get("reply", "")
        history.append({"role": "assistant", "content": next_reply})
        context.user_data["conversation_history"] = history

        if next_reply:
            await msg_target.reply_text(
                next_reply,
                parse_mode="Markdown",
                reply_markup=skip_keyboard(f"skip_followup_{next_state}"),
            )
        return next_state

    return await _ask_research_design(update, context)


# ─── Followup state bindings ─────────────────────────────────────────────────

async def handle_followup_1_text(u, c):  return await handle_followup_text(u, c, ASK_FOLLOWUP_1)
async def handle_followup_1_voice(u, c): return await handle_followup_voice(u, c, ASK_FOLLOWUP_1)
async def handle_followup_1_skip(u, c):  return await handle_followup_skip(u, c, ASK_FOLLOWUP_1)

async def handle_followup_2_text(u, c):  return await handle_followup_text(u, c, ASK_FOLLOWUP_2)
async def handle_followup_2_voice(u, c): return await handle_followup_voice(u, c, ASK_FOLLOWUP_2)
async def handle_followup_2_skip(u, c):  return await handle_followup_skip(u, c, ASK_FOLLOWUP_2)

async def handle_followup_3_text(u, c):  return await handle_followup_text(u, c, ASK_FOLLOWUP_3)
async def handle_followup_3_voice(u, c): return await handle_followup_voice(u, c, ASK_FOLLOWUP_3)
async def handle_followup_3_skip(u, c):  return await handle_followup_skip(u, c, ASK_FOLLOWUP_3)


# ─── STEP 9: Supervisor context ───────────────────────────────────────────────

async def handle_supervisor_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[onboarding] Supervisor context: '{text[:80]}' | user={user_id}")

    if text.lower() not in ("skip", "s", ""):
        context.user_data["supervisor_context"] = text

    return await _ask_research_design(update, context)


async def handle_supervisor_skip(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    print(f"[onboarding] Supervisor skipped | user={query.from_user.id}")
    return await _ask_research_design(update, context, message=query.message)


# ─── STEP 10: Research design ─────────────────────────────────────────────────

async def _ask_research_design(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message=None,
) -> int:
    print("[onboarding] _ask_research_design")
    msg_target = message or update.message

    existing = context.user_data.get("research_type", "")
    if existing and existing != "help_choose":
        return await _ask_citation(update, context, message=msg_target)

    await msg_target.reply_text(
        get_research_design_prompt_message(),
        parse_mode="Markdown",
        reply_markup=research_design_keyboard(),
    )
    return ASK_RESEARCH_DESIGN


async def handle_research_design(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query   = update.callback_query
    await query.answer()
    design  = query.data.replace("design_", "")
    user_id = query.from_user.id
    print(f"[onboarding] Research design: {design} | user={user_id}")

    if design == "help_choose":
        try:
            recommendation = await recommend_research_design(
                topic=context.user_data.get("topic", ""),
                department=context.user_data.get("department", ""),
                research_question=context.user_data.get("research_question", ""),
            )
        except Exception as e:
            print(f"[onboarding] recommend_research_design error: {e}")
            recommendation = "Quantitative research design using a structured questionnaire is recommended."

        await query.edit_message_text(
            get_research_design_prompt_message(recommendation),
            parse_mode="Markdown",
            reply_markup=research_design_keyboard(),
        )
        return ASK_RESEARCH_DESIGN

    context.user_data["research_type"] = design
    return await _ask_citation(update, context, message=query.message)


# ─── STEP 11: Citation style ──────────────────────────────────────────────────

async def _ask_citation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message=None,
) -> int:
    print("[onboarding] _ask_citation")
    msg_target = message or update.message

    existing = context.user_data.get("citation_style", "")
    if existing and existing != "not_sure":
        return await _ask_turnitin(update, context, message=msg_target)

    await msg_target.reply_text(
        get_citation_prompt_message(),
        parse_mode="Markdown",
        reply_markup=citation_keyboard(),
    )
    return ASK_CITATION


async def handle_citation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query    = update.callback_query
    await query.answer()
    citation = query.data.replace("cite_", "")
    user_id  = query.from_user.id
    print(f"[onboarding] Citation: {citation} | user={user_id}")

    context.user_data["citation_style"] = citation
    return await _ask_turnitin(update, context, message=query.message)


# ─── STEP 12: Turnitin ────────────────────────────────────────────────────────

async def _ask_turnitin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message=None,
) -> int:
    print("[onboarding] _ask_turnitin")
    msg_target = message or update.message

    if "turnitin" in context.user_data:
        return await _show_brief_confirmation(update, context, message=msg_target)

    await msg_target.reply_text(
        get_turnitin_prompt_message(),
        parse_mode="Markdown",
        reply_markup=turnitin_keyboard(),
    )
    return CONFIRM_BRIEF


async def handle_turnitin(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query    = update.callback_query
    await query.answer()
    turnitin = query.data == "turnitin_yes"
    user_id  = query.from_user.id
    print(f"[onboarding] Turnitin: {turnitin} | user={user_id}")

    context.user_data["turnitin"] = turnitin
    return await _show_brief_confirmation(update, context, message=query.message)


# ─── STEP 13: Brief confirmation ──────────────────────────────────────────────

async def _show_brief_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message=None,
) -> int:
    print("[onboarding] _show_brief_confirmation")
    user_id    = update.effective_user.id if update.effective_user else None
    msg_target = message or update.message

    topic       = context.user_data.get("topic", "")
    retry_count = context.user_data.get("topic_retry_count", 0)

    # AI topic validation
    if topic and retry_count < MAX_TOPIC_RETRIES:
        await msg_target.reply_text("Validating your topic... ⏳")
        try:
            validation = await validate_topic_with_ai(
                topic=topic,
                department=context.user_data.get("department", ""),
                level=context.user_data.get("academic_level", ""),
                university=context.user_data.get("university", ""),
            )
        except Exception as e:
            print(f"[onboarding] validate_topic_with_ai error: {e}")
            validation = {"is_valid": True}

        if not validation.get("is_valid"):
            context.user_data["topic_retry_count"] = retry_count + 1
            await msg_target.reply_text(
                get_validation_failed_message(
                    validation.get("feedback", ""),
                    validation.get("suggestions", []),
                ),
                parse_mode="Markdown",
            )
            await msg_target.reply_text("Type your revised topic:")
            return ASK_TOPIC_OPEN

    # Show brief card
    brief     = extract_brief_from_context(context.user_data)
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


# ─── CONFIRM BRIEF & HAND OFF ─────────────────────────────────────────────────

async def handle_confirm_brief(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query   = update.callback_query
    await query.answer()
    action  = query.data
    user_id = query.from_user.id
    print(f"[onboarding] Confirm brief action: {action} | user={user_id}")

    if action == "change_topic":
        context.user_data.pop("topic", None)
        context.user_data.pop("research_question", None)
        await query.edit_message_text(
            "No problem. Tell me your revised topic (type or send a voice note):",
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
                "Something went wrong saving your project. Please send /start and try again."
            )
            return ConversationHandler.END

        # Mark onboarding complete — prevents global handler from intercepting
        context.user_data["onboarding_complete"]  = True
        context.user_data["conversation_history"] = []

        print(f"[onboarding] Project created for {user_id}. Handing off to chapter handler.")

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
                "Chapter 1 generation failed. Send /start and tap Continue — "
                "your project is saved and you can try again."
            )

        return ConversationHandler.END

    return CONFIRM_BRIEF


# ─── CONVERSATION HANDLER BUILDER ────────────────────────────────────────────

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
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic_open_text),
                MessageHandler(filters.VOICE, handle_topic_open_voice),
            ],
            ASK_FOLLOWUP_1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_followup_1_text),
                MessageHandler(filters.VOICE, handle_followup_1_voice),
                CallbackQueryHandler(handle_followup_1_skip, pattern="^skip_followup_1$"),
            ],
            ASK_FOLLOWUP_2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_followup_2_text),
                MessageHandler(filters.VOICE, handle_followup_2_voice),
                CallbackQueryHandler(handle_followup_2_skip, pattern="^skip_followup_2$"),
            ],
            ASK_FOLLOWUP_3: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_followup_3_text),
                MessageHandler(filters.VOICE, handle_followup_3_voice),
                CallbackQueryHandler(handle_followup_3_skip, pattern="^skip_followup_3$"),
            ],
            ASK_SUPERVISOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_supervisor_text),
                CallbackQueryHandler(handle_supervisor_skip, pattern="^skip_supervisor$"),
            ],
            ASK_RESEARCH_DESIGN: [
                CallbackQueryHandler(handle_research_design, pattern="^design_"),
            ],
            ASK_CITATION: [
                CallbackQueryHandler(handle_citation, pattern="^cite_"),
            ],
            CONFIRM_BRIEF: [
                CallbackQueryHandler(handle_turnitin, pattern="^turnitin_"),
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