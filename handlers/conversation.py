print("[conversation.py] Loading global conversation handler...")

import json
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from services.supabase_service import (
    get_active_project, is_subscribed, get_user,
    save_chapter_content, update_project, get_session,
)
from services.claude_service import run_conversation_agent
from services.whisper_service import (
    transcribe_voice_message,
    build_voice_received_message,
    build_transcription_preview,
)
from utils.keyboards import payment_plans_keyboard
from utils.constants import CHAPTER_NAMES


# ─── FREE USER NUDGE ──────────────────────────────────────────────────────────

FREE_USER_NUDGE = (
    "👋 I can see you have a question.\n\n"
    "Free access includes *Chapter 1 and 2 generation* with buttons.\n\n"
    "With a paid subscription you get:\n"
    "✅ Full AI conversation — ask me anything about your project\n"
    "✅ Supervisor correction mode — paste feedback, I fix the chapter\n"
    "✅ Unlimited chapter editing and refinements\n"
    "✅ Chapters 3, 4 and 5 generation\n"
    "✅ Voice note support throughout\n"
    "✅ PDF download of your complete project\n"
    "✅ Project defence preparation\n\n"
    "Upgrade to unlock the full research assistant:"
)


# ─── ONBOARDING STATE DETECTION ───────────────────────────────────────────────

def _user_is_onboarding(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """
    Check if the user is currently mid-onboarding.
    We check three signals:
    1. context.user_data has academic_level but not onboarding_complete
    2. context.user_data has conversation_history (intake agent is active)
    3. Supabase session state is not idle/onboarded
    Any one of these means we must not intercept the message.
    """
    ud = context.user_data

    # Signal 1: onboarding explicitly marked complete
    if ud.get("onboarding_complete"):
        return False

    # Signal 2: intake agent conversation is active
    if ud.get("conversation_history") and len(ud.get("conversation_history", [])) > 0:
        return True

    # Signal 3: user has partial onboarding data in context
    onboarding_keys = ["academic_level", "faculty", "department", "university"]
    if any(ud.get(k) for k in onboarding_keys):
        return True

    return False


# ─── MAIN HANDLER ─────────────────────────────────────────────────────────────

async def handle_global_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Global fallback handler for all text and voice messages
    that didn't match any ConversationHandler state.

    Guards:
    1. Skip if user is mid-onboarding
    2. Skip if user has no active project
    3. Free users → paywall nudge
    4. Paid users → full conversational AI assistant
    """
    if not update.message:
        return

    user_id = update.effective_user.id
    print(f"[conversation] global message from user={user_id}")

    # ── Guard 1: Skip if mid-onboarding ──────────────────────────────────────
    if _user_is_onboarding(context, user_id):
        print(f"[conversation] User {user_id} is mid-onboarding — skipping")
        return

    # ── Guard 2: Must have an active project ─────────────────────────────────
    project = get_active_project(user_id)
    if not project:
        print(f"[conversation] No active project for {user_id} — skipping")
        return

    # ── Guard 3: Subscription check ───────────────────────────────────────────
    if not is_subscribed(user_id):
        print(f"[conversation] Free user {user_id} — showing nudge")
        await update.message.reply_text(
            FREE_USER_NUDGE,
            parse_mode="Markdown",
            reply_markup=payment_plans_keyboard(),
        )
        return

    # ── Route to voice or text handler ────────────────────────────────────────
    if update.message.voice:
        await _handle_voice(update, context, project)
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    await _handle_text(update, context, text, project)


# ─── VOICE HANDLER ────────────────────────────────────────────────────────────

async def _handle_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project: dict,
) -> None:
    voice = update.message.voice
    user_id = update.effective_user.id
    print(f"[conversation] voice: {voice.duration}s | user={user_id}")

    processing_msg = await update.message.reply_text(
        build_voice_received_message(voice.duration)
    )

    try:
        result = await transcribe_voice_message(
            bot=context.bot,
            file_id=voice.file_id,
        )
    except Exception as e:
        print(f"[conversation] Voice transcription exception: {e}")
        await processing_msg.edit_text(
            "I couldn't process that voice note. Please try again or type your message."
        )
        return

    if not result["success"]:
        await processing_msg.edit_text(
            "I couldn't transcribe that voice note. "
            "Please try again or type your message."
        )
        return

    transcript = result["transcript"]
    print(f"[conversation] Transcript: '{transcript[:100]}'")

    await processing_msg.edit_text(
        build_transcription_preview(transcript),
        parse_mode="Markdown",
    )

    await _handle_text(update, context, transcript, project)


# ─── TEXT HANDLER ─────────────────────────────────────────────────────────────

async def _handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    project: dict,
) -> None:
    user_id = update.effective_user.id
    print(f"[conversation] text: '{text[:80]}' | user={user_id}")

    user = get_user(user_id)

    # Load or init conversation history
    if "chat_history" not in context.user_data:
        context.user_data["chat_history"] = []

    history = context.user_data["chat_history"]
    history.append({"role": "user", "content": text})

    # Keep last 20 turns
    if len(history) > 20:
        history = history[-20:]
    context.user_data["chat_history"] = history

    # Typing indicator
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing",
        )
    except Exception:
        pass

    # Build brief
    try:
        from handlers.chapters import _project_to_brief
        brief = _project_to_brief(project, user)
    except Exception as e:
        print(f"[conversation] _project_to_brief error: {e}")
        brief = {"topic": project.get("topic", "")}

    # Run agent
    print(f"[conversation] Running conversation agent. History: {len(history)} turns")
    try:
        result = await run_conversation_agent(
            history=history,
            brief=brief,
            user=user,
            project=project,
        )
    except Exception as e:
        print(f"[conversation] run_conversation_agent exception: {e}")
        await update.message.reply_text(
            "I had a problem processing that. Could you try again?"
        )
        return

    reply       = result.get("reply", "")
    action      = result.get("action", "none")
    action_data = result.get("action_data", {})

    print(f"[conversation] reply_len={len(reply)} action={action}")

    # Add to history
    if reply:
        history.append({"role": "assistant", "content": reply})
        context.user_data["chat_history"] = history

    # ── Execute action ────────────────────────────────────────────────────────
    try:
        if action == "edit_chapter":
            await _execute_chapter_edit(update, context, project, brief, action_data, reply)
            return

        if action == "generate_chapter":
            chapter_number = action_data.get("chapter_number")
            if chapter_number and isinstance(chapter_number, int) and 1 <= chapter_number <= 5:
                if reply:
                    await update.message.reply_text(reply, parse_mode="Markdown")
                from handlers.chapters import _generate_and_deliver_chapter
                await _generate_and_deliver_chapter(
                    user_id=user_id,
                    chapter_number=chapter_number,
                    context=context,
                    send_target=update.message,
                )
                return

        if action == "download_pdf":
            if reply:
                await update.message.reply_text(reply, parse_mode="Markdown")
            await _send_pdf(update, context, project, user)
            return

        if action == "show_paywall":
            await update.message.reply_text(
                reply or FREE_USER_NUDGE,
                parse_mode="Markdown",
                reply_markup=payment_plans_keyboard(),
            )
            return

    except Exception as e:
        print(f"[conversation] Action execution error: {e}")
        await update.message.reply_text(
            "Something went wrong while processing that. Please try again."
        )
        return

    # Default — send reply
    if reply:
        try:
            from utils.helpers import send_long_message
            await send_long_message(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                text=reply,
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"[conversation] send_long_message error: {e}")
            await update.message.reply_text(reply[:4000])


# ─── CHAPTER EDIT ─────────────────────────────────────────────────────────────

async def _execute_chapter_edit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project: dict,
    brief: dict,
    action_data: dict,
    initial_reply: str,
) -> None:
    user_id        = update.effective_user.id
    chapter_number = action_data.get("chapter_number")
    correction     = action_data.get("correction_summary", "")

    print(f"[conversation] chapter edit: ch={chapter_number} user={user_id}")

    if not chapter_number or not isinstance(chapter_number, int):
        if initial_reply:
            await update.message.reply_text(initial_reply, parse_mode="Markdown")
        return

    if not 1 <= chapter_number <= 5:
        await update.message.reply_text(
            f"Chapter {chapter_number} doesn't exist. Projects have Chapters 1–5."
        )
        return

    chapter_content = project.get(f"chapter_{chapter_number}_content", "")
    if not chapter_content:
        await update.message.reply_text(
            f"Chapter {chapter_number} hasn't been generated yet. "
            f"Generate it first, then I can edit it."
        )
        return

    if initial_reply:
        await update.message.reply_text(initial_reply, parse_mode="Markdown")

    status_msg = await update.message.reply_text(
        f"✍️ Applying corrections to Chapter {chapter_number}... ⏳"
    )

    try:
        from services.claude_service import run_correction_agent
        corrected = await run_correction_agent(
            mode="correct",
            chapter_number=chapter_number,
            chapter_content=chapter_content,
            correction_request=correction,
            correction_history=[],
        )
    except Exception as e:
        print(f"[conversation] run_correction_agent error: {e}")
        await status_msg.edit_text(
            "Something went wrong during editing. Your original chapter is unchanged."
        )
        return

    if not corrected:
        await status_msg.edit_text(
            "Something went wrong during editing. Please try again."
        )
        return

    # Save
    try:
        save_chapter_content(user_id, chapter_number, corrected)
        print(f"[conversation] Chapter {chapter_number} saved after edit")
    except Exception as e:
        print(f"[conversation] save_chapter_content error: {e}")

    try:
        await status_msg.delete()
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ *Chapter {chapter_number} updated.* Here's the revised version:",
        parse_mode="Markdown",
    )

    try:
        from utils.helpers import send_long_message
        await send_long_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            text=corrected,
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[conversation] send corrected chapter error: {e}")
        await update.message.reply_text(corrected[:4000])

    await update.message.reply_text(
        "How does that look? Tell me if anything else needs changing.",
    )


# ─── PDF SEND ─────────────────────────────────────────────────────────────────

async def _send_pdf(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project: dict,
    user: dict,
) -> None:
    try:
        from services.pdf_service import generate_project_pdf
        if user:
            project["university"]     = project.get("university")     or user.get("university", "")
            project["department"]     = project.get("department")     or user.get("department", "")
            project["academic_level"] = project.get("academic_level") or user.get("academic_level", "bsc")
            project["faculty"]        = project.get("faculty")        or user.get("faculty", "")

        pdf_buffer    = generate_project_pdf(project, user)
        chapters_done = project.get("chapters_completed", 0)
        topic_slug    = project.get("topic", "project")[:25].replace(" ", "_")

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=pdf_buffer,
            filename=f"FYP_{topic_slug}.pdf",
            caption=f"📄 Your project PDF — Chapters 1–{chapters_done}",
        )
    except Exception as e:
        print(f"[conversation] _send_pdf error: {e}")
        await update.message.reply_text(
            "PDF generation failed. Try again in a moment."
        )


# ─── REGISTRATION ─────────────────────────────────────────────────────────────

def register_conversation_handler(application) -> None:
    print("[conversation] Registering global conversation handler at group 2...")
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.VOICE) & ~filters.COMMAND,
            handle_global_message,
        ),
        group=2,
    )
    print("[conversation] Global conversation handler registered.")


print("[conversation.py] Global conversation handler loaded.")