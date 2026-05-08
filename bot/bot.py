print("[bot.py] Loading bot builder...")

from telegram.ext import Application, CallbackQueryHandler
from config import TELEGRAM_BOT_TOKEN
from handlers.onboarding import get_onboarding_handler
from handlers.corrections import get_correction_handler
from handlers.chapters import register_chapter_handlers
from handlers.payments import register_payment_handlers
from handlers.admin import register_admin_handlers
from handlers.conversation import register_conversation_handler


def build_application() -> Application:
    print("[bot] Building PTB Application...")

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # ── Group 0: Onboarding conversation (highest priority) ───────────────────
    application.add_handler(get_onboarding_handler(), group=0)
    print("[bot] Onboarding handler registered at group 0")

    # ── Group 0: Correction conversation ──────────────────────────────────────
    application.add_handler(get_correction_handler(), group=0)
    print("[bot] Correction handler registered at group 0")

    # ── Group 1: Chapter handlers (includes ch4 data input at group=1) ────────
    register_chapter_handlers(application)
    print("[bot] Chapter handlers registered")

    # ── Group 2: Payment handlers ──────────────────────────────────────────────
    register_payment_handlers(application)
    print("[bot] Payment handlers registered")

    # ── Group 3: Admin commands ────────────────────────────────────────────────
    register_admin_handlers(application)
    print("[bot] Admin handlers registered")

    # ── Restart callback (global) ─────────────────────────────────────────────
    async def handle_restart(update, context):
        query = update.callback_query
        await query.answer()
        from services.supabase_service import clear_session
        clear_session(query.from_user.id)
        context.user_data.clear()
        await query.edit_message_text(
            "Session cleared. Send /start to begin a new project."
        )

    application.add_handler(
        CallbackQueryHandler(handle_restart, pattern="^restart$"),
        group=2,
    )

    # ── Group 2: Global conversational handler (paid users) ───────────────────
    register_conversation_handler(application)
    print("[bot] Global conversation handler registered")

    print("[bot] Application built successfully.")
    return application


print("[bot.py] Bot builder loaded.")