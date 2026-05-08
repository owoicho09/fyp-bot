print("[conversation.py] Loading global conversation handler...")

import json
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from services.supabase_service import (
    get_active_project, is_subscribed, get_user,
    update_project, save_chapter_content,
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
    "✅ Supervisor correction mode — paste feedback, I fix chapter by chapter\n"
    "✅ Chapter editing — unlimited back-and-forth refinements\n"
    "✅ Chapters 3, 4 and 5 generation\n"
    "✅ Voice note support throughout\n"
    "✅ PDF download of complete project\n\n"
    "✅ Prepare for Project defence\n\n"

    "Upgrade to unlock the full research assistant:"
)


# ─── MAIN HANDLER ─────────────────────────────────────────────────────────────

async def handle_global_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Global fallback handler for all text and voice messages
    that didn't match any ConversationHandler state.

    Free users → paywall nudge
    Paid users → full conversational AI assistant
    """
    user_id = update.effective_user.id
    print(f"[conversation] global message from user={user_id}")

    # Check subscription
    if not is_subscribed(user_id):
        print(f"[conversation] Free user {user_id} — showing nudge")
        await update.message.reply_text(
            FREE_USER_NUDGE,
            parse_mode="Markdown",
            reply_markup=payment_plans_keyboard(),
        )
        return

    # Handle voice note
    if update.message.voice:
        await _handle_voice(update, context)
        return

    # Handle text
    text = update.message.text.strip()
    if not text:
        return

    await _handle_text(update, context, text)


async def _handle_voice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Transcribe voice and pass to conversation agent."""
    voice = update.message.voice
    user_id = update.effective_user.id
    print(f"[conversation] voice message: {voice.duration}s | user={user_id}")

    processing_msg = await update.message.reply_text(
        build_voice_received_message(voice.duration)
    )

    result = await transcribe_voice_message(
        bot=context.bot,
        file_id=voice.file_id,
    )

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

    await _handle_text(update, context, transcript)


async def _handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    """
    Core conversational handler for paid users.
    Loads full project context, runs conversation agent,
    executes any actions the agent decides on.
    """
    user_id = update.effective_user.id
    print(f"[conversation] Processing text: '{text[:80]}' | user={user_id}")

    # Load project and user context
    project = get_active_project(user_id)
    user    = get_user(user_id)

    if not project:
        await update.message.reply_text(
            "I don't see an active project for you. "
            "Send /start to begin or continue your project."
        )
        return

    # Load or initialise conversation history from context
    if "chat_history" not in context.user_data:
        context.user_data["chat_history"] = []

    history = context.user_data["chat_history"]

    # Add student message to history
    history.append({"role": "user", "content": text})

    # Keep history manageable — last 20 turns
    if len(history) > 20:
        history = history[-20:]
        context.user_data["chat_history"] = history

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    # Build project brief for context injection
    from handlers.chapters import _project_to_brief
    brief = _project_to_brief(project)

    # Run conversation agent
    print(f"[conversation] Running conversation agent. History length: {len(history)}")
    result = await run_conversation_agent(
        history=history,
        brief=brief,
        user=user,
        project=project,
    )

    reply        = result.get("reply", "")
    action       = result.get("action", "none")
    action_data  = result.get("action_data", {})

    print(f"[conversation] Agent reply length={len(reply)} action={action}")

    # Add agent reply to history
    history.append({"role": "assistant", "content": reply})
    context.user_data["chat_history"] = history

    # ── Execute any actions the agent decided on ──────────────────────────────
    if action == "edit_chapter":
        await _execute_chapter_edit(
            update, context, project, brief, action_data, reply
        )
        return

    if action == "generate_chapter":
        chapter_number = action_data.get("chapter_number")
        if chapter_number:
            await update.message.reply_text(reply, parse_mode="Markdown")
            from handlers.chapters import _generate_and_deliver_chapter
            await _generate_and_deliver_chapter(
                user_id=user_id,
                chapter_number=chapter_number,
                context=context,
                send_target=update.message,
            )
            return

    if action == "show_paywall":
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=payment_plans_keyboard(),
        )
        return

    if action == "download_pdf":
        await update.message.reply_text(reply, parse_mode="Markdown")
        await _send_pdf(update, context, project, user)
        return

    # Default — just send the reply
    if reply:
        from utils.helpers import send_long_message
        await send_long_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            text=reply,
            parse_mode="Markdown",
        )


async def _execute_chapter_edit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project: dict,
    brief: dict,
    action_data: dict,
    initial_reply: str,
) -> None:
    """
    Execute a chapter edit triggered by the conversation agent.
    The agent already understood what needs to change —
    we go straight to applying the correction.
    """
    user_id        = update.effective_user.id
    chapter_number = action_data.get("chapter_number")
    correction     = action_data.get("correction_summary", "")

    print(f"[conversation] Executing chapter edit: ch={chapter_number} user={user_id}")

    if not chapter_number:
        await update.message.reply_text(initial_reply, parse_mode="Markdown")
        return

    chapter_content = project.get(f"chapter_{chapter_number}_content", "")
    if not chapter_content:
        await update.message.reply_text(
            f"Chapter {chapter_number} hasn't been generated yet. "
            f"Generate it first, then I can edit it."
        )
        return

    # Show what we understood
    await update.message.reply_text(
        initial_reply,
        parse_mode="Markdown",
    )

    status_msg = await update.message.reply_text(
        f"✍️ Applying corrections to Chapter {chapter_number}... ⏳"
    )

    from services.claude_service import run_correction_agent
    corrected = await run_correction_agent(
        mode="correct",
        chapter_number=chapter_number,
        chapter_content=chapter_content,
        correction_request=correction,
        correction_history=[],
    )

    if not corrected:
        await status_msg.edit_text(
            "Something went wrong during editing. Please try again."
        )
        return

    # Save corrected chapter
    save_chapter_content(user_id, chapter_number, corrected)
    print(f"[conversation] Chapter {chapter_number} edited and saved")

    await status_msg.delete()

    await update.message.reply_text(
        f"✅ *Chapter {chapter_number} updated.* Here's the revised version:",
        parse_mode="Markdown",
    )

    from utils.helpers import send_long_message
    await send_long_message(
        bot=context.bot,
        chat_id=update.effective_chat.id,
        text=corrected,
        parse_mode="Markdown",
    )

    await update.message.reply_text(
        "How does that look? Tell me if anything else needs changing.",
    )


async def _send_pdf(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project: dict,
    user: dict,
) -> None:
    """Send the project PDF."""
    try:
        from services.pdf_service import generate_project_pdf
        if user:
            project["university"]     = project.get("university")     or user.get("university", "")
            project["department"]     = project.get("department")     or user.get("department", "")
            project["academic_level"] = project.get("academic_level") or user.get("academic_level", "bsc")
        pdf_buffer  = generate_project_pdf(project, user)
        chapters_done = project.get("chapters_completed", 0)
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=pdf_buffer,
            filename=f"FYP_{project['topic'][:25].replace(' ','_')}.pdf",
            caption=f"📄 Your project PDF — Chapters 1–{chapters_done}",
        )
    except Exception as e:
        print(f"[conversation] PDF send error: {e}")
        await update.message.reply_text(
            "PDF generation failed. Try again in a moment."
        )


# ─── HANDLER REGISTRATION ─────────────────────────────────────────────────────

def register_conversation_handler(application) -> None:
    """
    Register the global conversation handler at group 2.
    Groups 0 and 1 handle ConversationHandlers and Chapter 4 data input.
    Group 2 catches everything else.
    """
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