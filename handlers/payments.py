print("[payments.py] Loading payments handler...")

from datetime import datetime, timezone, timedelta
from telegram import Update, LabeledPrice
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    CommandHandler, PreCheckoutQueryHandler,
    MessageHandler, filters,
)
from services.supabase_service import (
    get_user, update_user, get_active_project,
)
from utils.keyboards import payment_plans_keyboard
from utils.helpers import format_paywall_message
from config import PLANS


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _calculate_expiry(plan_key: str) -> str:
    days   = PLANS.get(plan_key, {}).get("days", 7)
    expiry = datetime.now(timezone.utc) + timedelta(days=days)
    print(f"[payments] _calculate_expiry: plan={plan_key} days={days} expires={expiry.isoformat()}")
    return expiry.isoformat()


def _continue_keyboard(user_id: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from utils.constants import CHAPTER_NAMES
    project = get_active_project(user_id)
    next_ch = 3
    if project:
        done    = project.get("chapters_completed", 0)
        next_ch = min(max(3, done + 1), 5)
    name = CHAPTER_NAMES.get(next_ch, f"Chapter {next_ch}")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"📖 Continue — Chapter {next_ch}: {name}",
            callback_data=f"gen_chapter_{next_ch}",
        )
    ]])


def _grant_access(user_id: int, plan_key: str) -> None:
    """Write subscription to Supabase."""
    expires_at = _calculate_expiry(plan_key)
    update_user(user_id, {
        "subscription_status":     "active",
        "subscription_plan":       plan_key,
        "subscription_expires_at": expires_at,
    })
    print(f"[payments] Access granted: user={user_id} plan={plan_key} expires={expires_at}")


# ─── PLAN SELECTION ───────────────────────────────────────────────────────────

async def handle_plan_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Student taps a plan button.
    Sends a Telegram Stars invoice directly in the chat.
    Price shown as Naira value — Stars shown in description.
    """
    query    = update.callback_query
    await query.answer()
    plan_key = query.data.replace("pay_", "")
    user_id  = query.from_user.id
    print(f"[payments] Plan selected: {plan_key} | user={user_id}")

    plan = PLANS.get(plan_key)
    if not plan:
        await query.message.reply_text("Invalid plan. Please try again.")
        return

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    stars       = plan["stars"]
    naira       = plan["naira"]
    name        = plan["name"]
    description = plan["description"]
    days        = plan["days"]

    # Send Telegram Stars invoice
    # provider_token="" means Telegram Stars (not card payments)
    await context.bot.send_invoice(
        chat_id=user_id,
        title=f"FYP Mentor — {name}",
        description=(
            f"{naira} • {description}\n\n"
            f"Valid for {days} days after payment.\n"
            f"Payment processed securely by Telegram."
        ),
        payload=f"fyp_{plan_key}_{user_id}",
        provider_token="",          # Empty string = Telegram Stars
        currency="XTR",             # XTR is the currency code for Telegram Stars
        prices=[
            LabeledPrice(
                label=f"{name} — {naira}",
                amount=stars,       # Amount in Stars
            )
        ],
        protect_content=False,
    )

    print(f"[payments] Invoice sent: plan={plan_key} stars={stars} user={user_id}")


# ─── PRE-CHECKOUT QUERY ───────────────────────────────────────────────────────

async def handle_pre_checkout(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Telegram sends this before charging the student.
    Must be answered within 10 seconds — always approve.
    """
    query = update.pre_checkout_query
    user_id = query.from_user.id
    print(f"[payments] PreCheckoutQuery: user={user_id} payload={query.invoice_payload}")

    # Always approve — Telegram handles fraud prevention
    await query.answer(ok=True)
    print(f"[payments] PreCheckoutQuery approved for user={user_id}")


# ─── SUCCESSFUL PAYMENT ───────────────────────────────────────────────────────

async def handle_successful_payment(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Telegram sends this after Stars payment is confirmed.
    Grant access immediately — no external verification needed.
    """
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    payload = payment.invoice_payload
    stars   = payment.total_amount

    print(f"[payments] SuccessfulPayment: user={user_id} payload={payload} stars={stars}")

    # Extract plan from payload — format: "fyp_{plan_key}_{user_id}"
    try:
        parts    = payload.split("_")
        plan_key = parts[1]
    except Exception as e:
        print(f"[payments] Could not parse plan from payload '{payload}': {e}")
        plan_key = "weekly"  # safe fallback

    plan = PLANS.get(plan_key, PLANS["weekly"])

    # Grant subscription access
    _grant_access(user_id, plan_key)

    # Confirm to student
    await update.message.reply_text(
        f"🎉 *Payment confirmed — {plan['naira']} received!*\n\n"
        f"Your *{plan['name']}* is now active.\n\n"
        f"✅ Chapters 3, 4 and 5 are unlocked\n"
        f"✅ Unlimited chapter corrections\n"
        f"✅ Voice note support\n"
        f"✅ Word document download\n\n"
        f"Tap below to continue your project:",
        parse_mode="Markdown",
        reply_markup=_continue_keyboard(user_id),
    )

    print(f"[payments] Access granted and confirmed to user {user_id}")


# ─── COMMANDS ─────────────────────────────────────────────────────────────────

async def handle_subscribe_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/subscribe — show payment plans."""
    user_id = update.effective_user.id
    print(f"[payments] /subscribe: user={user_id}")
    await update.message.reply_text(
        format_paywall_message(),
        parse_mode="Markdown",
        reply_markup=payment_plans_keyboard(),
    )


async def handle_my_subscription(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/subscription — show current subscription status."""
    user_id = update.effective_user.id
    print(f"[payments] /subscription: user={user_id}")

    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Send /start to begin.")
        return

    status  = user.get("subscription_status", "inactive")
    plan    = user.get("subscription_plan", "")
    expires = user.get("subscription_expires_at", "")

    print(f"[payments] /subscription: status={status} plan={plan} expires={expires}")
    if status == "active" and expires:
        try:
            exp_dt  = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            now     = datetime.now(timezone.utc)
            if exp_dt > now:
                days_left = (exp_dt - now).days
                plan_name = PLANS.get(plan, {}).get("name", plan)
                print(f"[payments] Active subscription: plan={plan_name} days_left={days_left}")
                await update.message.reply_text(
                    f"✅ *Subscription active*\n\n"
                    f"Plan: *{plan_name}*\n"
                    f"Expires: {exp_dt.strftime('%d %B %Y')}\n"
                    f"Days remaining: *{days_left}*",
                    parse_mode="Markdown",
                )
                return
        except Exception as e:
            print(f"[payments] Expiry parse error: {e}")

    await update.message.reply_text(
        "You do not have an active subscription.\n\n"
        "Chapters 1 and 2 are always free.\n"
        "Subscribe to unlock Chapters 3, 4 and 5:",
        reply_markup=payment_plans_keyboard(),
    )


# ─── HANDLER REGISTRATION ─────────────────────────────────────────────────────

def register_payment_handlers(application) -> None:
    print("[payments] Registering payment handlers...")

    # Plan selection buttons
    application.add_handler(
        CallbackQueryHandler(handle_plan_selection, pattern="^pay_")
    )

    # Telegram Stars checkout flow
    application.add_handler(
        PreCheckoutQueryHandler(handle_pre_checkout)
    )
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment)
    )

    # Commands
    application.add_handler(
        CommandHandler("subscribe", handle_subscribe_command)
    )
    application.add_handler(
        CommandHandler("subscription", handle_my_subscription)
    )

    print("[payments] Payment handlers registered.")


print("[payments.py] Payments handler loaded.")