print("[admin.py] Loading admin handler...")

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from services.supabase_service import (
    get_total_users, get_total_paid_users, get_total_projects,
    get_user,
)
from config import TELEGRAM_BOT_TOKEN

# ── Admin telegram IDs ────────────────────────────────────────────────────────
# Add your personal Telegram ID here to protect admin commands.
# Get your ID by messaging @userinfobot on Telegram.
ADMIN_IDS = {8075290595}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── /stats ───────────────────────────────────────────────────────────────────

async def handle_stats(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_id = update.effective_user.id
    print(f"[admin] /stats requested by {user_id}")

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    try:
        total_users  = get_total_users()
        paid_users   = get_total_paid_users()
        total_projects = get_total_projects()
        free_users   = total_users - paid_users
        conversion   = (
            round((paid_users / total_users) * 100, 1)
            if total_users > 0 else 0
        )

        await update.message.reply_text(
            f"📊 *FYP Mentor Stats*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Total users     : {total_users}\n"
            f"💳 Paid users      : {paid_users}\n"
            f"🆓 Free users      : {free_users}\n"
            f"📁 Total projects  : {total_projects}\n"
            f"📈 Conversion rate : {conversion}%\n",
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[admin] /stats error: {e}")
        await update.message.reply_text(f"Error fetching stats: {e}")


# ─── /broadcast ───────────────────────────────────────────────────────────────

async def handle_broadcast(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_id = update.effective_user.id
    print(f"[admin] /broadcast requested by {user_id}")

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /broadcast Your message here\n\n"
            "This will send a message to all registered users."
        )
        return

    message_text = " ".join(context.args)
    print(f"[admin] Broadcasting: '{message_text[:80]}'")

    # Fetch all user IDs from Supabase
    try:
        from services.supabase_service import supabase
        result = supabase.table("users").select("telegram_id").execute()
        user_ids = [row["telegram_id"] for row in result.data]
        print(f"[admin] Broadcasting to {len(user_ids)} users")
    except Exception as e:
        await update.message.reply_text(f"Failed to fetch users: {e}")
        return

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 *FYP Mentor Update*\n\n{message_text}",
                parse_mode="Markdown",
            )
            sent += 1
        except Exception as e:
            print(f"[admin] Broadcast failed for uid={uid}: {e}")
            failed += 1

    await update.message.reply_text(
        f"Broadcast complete.\n✅ Sent: {sent}\n❌ Failed: {failed}"
    )


# ─── /addadmin ────────────────────────────────────────────────────────────────

async def handle_addadmin(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Temporarily add an admin ID at runtime."""
    user_id = update.effective_user.id
    if not is_admin(user_id) and len(ADMIN_IDS) > 0:
        await update.message.reply_text("⛔ Unauthorised.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /addadmin <telegram_id>\n\n"
            f"Your current ID is: `{user_id}`",
            parse_mode="Markdown",
        )
        return

    try:
        new_admin = int(context.args[0])
        ADMIN_IDS.add(new_admin)
        print(f"[admin] Added admin: {new_admin}")
        await update.message.reply_text(f"✅ Admin added: `{new_admin}`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("Invalid Telegram ID — must be a number.")


# ─── /myid ────────────────────────────────────────────────────────────────────

async def handle_myid(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Let anyone check their Telegram ID — needed to set up admin."""
    user_id = update.effective_user.id
    print(f"[admin] /myid: user={user_id}")
    await update.message.reply_text(
        f"Your Telegram ID: `{user_id}`\n\n"
        "Share this with the bot operator to get admin access.",
        parse_mode="Markdown",
    )


# ─── HANDLER REGISTRATION ─────────────────────────────────────────────────────

def register_admin_handlers(application) -> None:
    print("[admin] Registering admin handlers...")
    application.add_handler(CommandHandler("stats",     handle_stats))
    application.add_handler(CommandHandler("broadcast", handle_broadcast))
    application.add_handler(CommandHandler("addadmin",  handle_addadmin))
    application.add_handler(CommandHandler("myid",      handle_myid))
    print("[admin] Admin handlers registered.")


print("[admin.py] Admin handler loaded.")