print("[corrections.py] Loading corrections handler...")

import json
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from services.supabase_service import (
    get_active_project, update_project, is_subscribed,
)
from services.claude_service import run_correction_agent
from services.whisper_service import (
    transcribe_voice_message,
    build_voice_received_message,
    build_transcription_preview,
)
from utils.constants import CHAPTER_NAMES

# ─── CONVERSATION STATES ──────────────────────────────────────────────────────
(
    CORRECTION_AWAITING_INPUT,
    CORRECTION_AWAITING_CONFIRM,
    CORRECTION_AWAITING_FEEDBACK,
) = range(20, 23)


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

async def handle_edit_chapter(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    chapter_number = int(query.data.replace("edit_chapter_", ""))
    print(f"[corrections] edit_chapter_{chapter_number}: user={user_id}")

    if not is_subscribed(user_id):
        await query.message.reply_text(
            "✏️ *Chapter editing is a premium feature.*\n\n"
            "Subscribe to edit and refine your chapters with supervisor "
            "feedback and unlimited corrections.",
            parse_mode="Markdown",
            reply_markup=_upgrade_keyboard(),
        )
        return ConversationHandler.END

    project = get_active_project(user_id)
    if not project:
        await query.message.reply_text("Could not find your project. Send /start.")
        return ConversationHandler.END

    chapter_content = project.get(f"chapter_{chapter_number}_content", "")
    if not chapter_content:
        await query.message.reply_text(
            f"Chapter {chapter_number} hasn't been generated yet."
        )
        return ConversationHandler.END

    context.user_data["correction_chapter"]  = chapter_number
    context.user_data["correction_original"] = chapter_content
    context.user_data["correction_current"]  = chapter_content
    context.user_data["correction_history"]  = []
    context.user_data["correction_round"]    = 1

    chapter_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")

    await query.message.reply_text(
        f"✏️ *Editing Chapter {chapter_number}: {chapter_name}*\n\n"
        f"Tell me what needs to change. You can:\n\n"
        f"• Paste your supervisor's exact comments\n"
        f"• Describe what you want improved\n"
        f"• Send a 🎙️ voice note explaining the corrections\n\n"
        f"Be as specific as possible — the more detail, the better the result.",
        parse_mode="Markdown",
        reply_markup=_cancel_keyboard(),
    )
    return CORRECTION_AWAITING_INPUT


# ─── RECEIVE CORRECTION INPUT ────────────────────────────────────────────────

async def handle_correction_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    user_id = update.effective_user.id
    print(f"[corrections] correction text from {user_id}: '{text[:80]}'")
    return await _process_correction_input(update, context, text)


async def handle_correction_voice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    voice = update.message.voice
    user_id = update.effective_user.id
    print(f"[corrections] correction voice from {user_id}: {voice.duration}s")

    processing_msg = await update.message.reply_text(
        build_voice_received_message(voice.duration)
    )
    result = await transcribe_voice_message(
        bot=context.bot,
        file_id=voice.file_id,
    )
    if not result["success"]:
        await processing_msg.edit_text(
            "Could not transcribe that voice note. Please type your correction instead."
        )
        return CORRECTION_AWAITING_INPUT

    transcript = result["transcript"]
    await processing_msg.edit_text(
        build_transcription_preview(transcript),
        parse_mode="Markdown",
    )
    return await _process_correction_input(update, context, transcript)


async def _process_correction_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    correction_request: str,
) -> int:
    user_id         = update.effective_user.id
    chapter_number  = context.user_data.get("correction_chapter")
    current_content = context.user_data.get("correction_current", "")
    history         = context.user_data.get("correction_history", [])
    round_num       = context.user_data.get("correction_round", 1)

    print(f"[corrections] Processing round {round_num} ch{chapter_number}")

    context.user_data["pending_correction_request"] = correction_request

    status_msg = await update.message.reply_text(
        "🔍 Analysing your correction request..."
    )

    print(f"[corrections] Calling run_correction_agent mode=understand ch={chapter_number}")
    try:
        understanding = await run_correction_agent(
            mode="understand",
            chapter_number=chapter_number,
            chapter_content=current_content,
            correction_request=correction_request,
            correction_history=history,
        )
    except Exception as e:
        print(f"[corrections] run_correction_agent understand ERROR: {e}")
        await status_msg.edit_text(
            "Something went wrong analysing your request. Please try again."
        )
        return CORRECTION_AWAITING_INPUT
    print(f"[corrections] Understanding result: {str(understanding)[:100]}")

    await status_msg.delete()

    context.user_data["correction_understanding"] = understanding

    await update.message.reply_text(
        f"📋 *Here's what I understood needs to change:*\n\n"
        f"{understanding}\n\n"
        f"Is this correct? Should I proceed?",
        parse_mode="Markdown",
        reply_markup=_confirm_correction_keyboard(),
    )
    return CORRECTION_AWAITING_CONFIRM


# ─── CONFIRM AND EXECUTE ──────────────────────────────────────────────────────

async def handle_correction_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    action  = query.data
    user_id = query.from_user.id
    print(f"[corrections] confirm: {action} | user={user_id}")

    if action == "correction_cancel":
        await query.edit_message_text("Correction cancelled. Your chapter is unchanged.")
        return ConversationHandler.END

    if action == "correction_clarify":
        await query.edit_message_text(
            "No problem. Please be more specific about what you want changed:\n\n"
            "• Which section exactly?\n"
            "• What did your supervisor say word for word?\n"
            "• What should it look like after the change?"
        )
        return CORRECTION_AWAITING_INPUT

    if action == "correction_confirm":
        chapter_number     = context.user_data.get("correction_chapter")
        current_content    = context.user_data.get("correction_current", "")
        correction_request = context.user_data.get("pending_correction_request", "")
        understanding      = context.user_data.get("correction_understanding", "")
        history            = context.user_data.get("correction_history", [])
        round_num          = context.user_data.get("correction_round", 1)

        await query.edit_message_text(
            f"✍️ Applying corrections to Chapter {chapter_number}... ⏳"
        )

        print(f"[corrections] Calling run_correction_agent mode=correct ch={chapter_number} round={round_num}")
        try:
            corrected_content = await run_correction_agent(
                mode="correct",
                chapter_number=chapter_number,
                chapter_content=current_content,
                correction_request=correction_request,
                correction_history=history,
            )
        except Exception as e:
            print(f"[corrections] run_correction_agent correct ERROR: {e}")
            await query.message.reply_text(
                "Something went wrong during editing. Your original chapter is unchanged. Please try again."
            )
            return ConversationHandler.END

        if not corrected_content:
            print(f"[corrections] run_correction_agent returned empty for ch={chapter_number}")
            await query.message.reply_text(
                "Something went wrong. Your original chapter is unchanged. Please try again."
            )
            return ConversationHandler.END

        # Update history and context
        history.append({
            "round":   round_num,
            "request": correction_request,
            "summary": understanding,
        })
        context.user_data["correction_history"] = history
        context.user_data["correction_current"] = corrected_content
        context.user_data["correction_round"]   = round_num + 1

        # Save to Supabase
        project = get_active_project(user_id)
        if project:
            existing = project.get("correction_history") or {}
            if isinstance(existing, str):
                try:
                    existing = json.loads(existing)
                except Exception:
                    existing = {}
            ch_key = str(chapter_number)
            if ch_key not in existing:
                existing[ch_key] = []
            existing[ch_key].append({
                "round":   round_num,
                "request": correction_request[:200],
            })
            update_project(user_id, {
                f"chapter_{chapter_number}_content": corrected_content,
                "correction_history": json.dumps(existing),
            })

        print(f"[corrections] Chapter {chapter_number} corrected. Round {round_num}")

        # Deliver corrected chapter
        await query.message.reply_text(
            f"✅ *Chapter {chapter_number} — Correction {round_num} applied*\n\n"
            f"Here is your revised chapter:",
            parse_mode="Markdown",
        )

        from utils.helpers import send_long_message
        await send_long_message(
            bot=context.bot,
            chat_id=query.message.chat_id,
            text=corrected_content,
            parse_mode="Markdown",
        )

        await query.message.reply_text(
            f"How does that look? You've made *{round_num}* correction(s) to this chapter.",
            parse_mode="Markdown",
            reply_markup=_post_correction_keyboard(chapter_number),
        )
        return CORRECTION_AWAITING_FEEDBACK

    return CORRECTION_AWAITING_CONFIRM


# ─── POST CORRECTION ──────────────────────────────────────────────────────────

async def handle_post_correction(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query   = update.callback_query
    await query.answer()
    action  = query.data
    user_id = query.from_user.id
    print(f"[corrections] post_correction: {action} | user={user_id}")

    if action == "correction_another":
        chapter_number = context.user_data.get("correction_chapter")
        chapter_name   = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")
        round_num      = context.user_data.get("correction_round", 2)
        await query.edit_message_text(
            f"✏️ *Correction round {round_num} — Chapter {chapter_number}: {chapter_name}*\n\n"
            f"What else needs to change?\n\n"
            f"Type, or send a 🎙️ voice note:",
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard(),
        )
        return CORRECTION_AWAITING_INPUT

    if action == "correction_download":
        await query.message.reply_text("Generating updated PDF... ⏳")
        project = get_active_project(user_id)
        if project:
            try:
                from services.pdf_service import generate_project_pdf
                from services.supabase_service import get_user
                user_record = get_user(user_id)
                if user_record:
                    project["university"]     = project.get("university")     or user_record.get("university", "")
                    project["department"]     = project.get("department")     or user_record.get("department", "")
                    project["academic_level"] = project.get("academic_level") or user_record.get("academic_level", "bsc")
                print(f"[corrections] Generating revised PDF for user={user_id}")
                pdf_buffer = generate_project_pdf(project, user_record)
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=pdf_buffer,
                    filename=f"FYP_Revised_{project['topic'][:25].replace(' ','_')}.pdf",
                    caption="📄 Your revised project PDF.",
                )
                print(f"[corrections] Revised PDF sent to user={user_id}")
            except Exception as e:
                print(f"[corrections] correction_download ERROR user={user_id}: {e}")
                await query.message.reply_text(
                    "PDF generation failed. Your chapter changes are saved — try downloading again."
                )
        else:
            print(f"[corrections] correction_download: no project found for user={user_id}")
        return ConversationHandler.END

    if action == "correction_done":
        await query.edit_message_text(
            "✅ *Chapter saved.* Your corrections have been applied.\n\n"
            "You can always come back to edit further anytime.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    return CORRECTION_AWAITING_FEEDBACK


# ─── KEYBOARDS ───────────────────────────────────────────────────────────────

def _confirm_correction_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, apply these corrections", callback_data="correction_confirm")],
        [InlineKeyboardButton("🔄 Not quite — let me clarify",   callback_data="correction_clarify")],
        [InlineKeyboardButton("❌ Cancel",                        callback_data="correction_cancel")],
    ])


def _post_correction_keyboard(chapter_number: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Make another correction",  callback_data="correction_another")],
        [InlineKeyboardButton("📥 Download updated PDF",     callback_data="correction_download")],
        [InlineKeyboardButton("✅ Done — save and continue", callback_data="correction_done")],
    ])


def _cancel_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel correction", callback_data="correction_cancel")
    ]])


def _upgrade_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💳 View subscription plans", callback_data="show_plans")
    ]])


# ─── CONVERSATION HANDLER BUILDER ────────────────────────────────────────────

def get_correction_handler() -> ConversationHandler:
    print("[corrections] Registering correction ConversationHandler...")
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_edit_chapter, pattern=r"^edit_chapter_\d+$")
        ],
        states={
            CORRECTION_AWAITING_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_correction_text),
                MessageHandler(filters.VOICE, handle_correction_voice),
                CallbackQueryHandler(handle_correction_confirm, pattern="^correction_cancel$"),
            ],
            CORRECTION_AWAITING_CONFIRM: [
                CallbackQueryHandler(
                    handle_correction_confirm,
                    pattern="^correction_(confirm|clarify|cancel)$",
                ),
            ],
            CORRECTION_AWAITING_FEEDBACK: [
                CallbackQueryHandler(
                    handle_post_correction,
                    pattern="^correction_(another|download|done)$",
                ),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handle_correction_confirm, pattern="^correction_cancel$"),
        ],
        allow_reentry=True,
        name="corrections",
        persistent=False,
    )


print("[corrections.py] Corrections handler loaded.")