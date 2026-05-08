print("[payments.py] Loading payments handler...")

import hmac
import hashlib
import json
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, CommandHandler
)
from services.supabase_service import (
    get_user, update_user, create_payment_record,
    confirm_payment, get_payment_by_reference,
    get_latest_payment, get_active_project,
)
from utils.keyboards import payment_plans_keyboard, payment_link_keyboard
from utils.helpers import format_paywall_message
from config import (
    PAYSTACK_SECRET_KEY, PAYSTACK_WEBHOOK_SECRET, PLANS
)
import httpx


# ─── PAYSTACK API ─────────────────────────────────────────────────────────────

PAYSTACK_INIT_URL   = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify"


async def _initialize_paystack_transaction(
    email: str,
    amount: int,
    reference: str,
    metadata: dict,
) -> dict:
    """
    Call Paystack's transaction initialize endpoint.
    Returns the authorization URL the student pays on.
    """
    print(f"[payments] Initializing Paystack: ref={reference} amount={amount}")
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email":     email,
        "amount":    amount,
        "reference": reference,
        "metadata":  metadata,
        "callback_url": "https://t.me/FinalYearProjectBuilder_bot",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                PAYSTACK_INIT_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            print(f"[payments] Paystack init response: status={data.get('status')}")
            return data
    except Exception as e:
        print(f"[payments] Paystack init error: {e}")
        raise


async def _verify_paystack_transaction(reference: str) -> dict:
    """Verify a transaction with Paystack's verify endpoint."""
    print(f"[payments] Verifying Paystack transaction: ref={reference}")
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{PAYSTACK_VERIFY_URL}/{reference}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            print(f"[payments] Paystack verify: status={data.get('data', {}).get('status')}")
            return data
    except Exception as e:
        print(f"[payments] Paystack verify error: {e}")
        raise


def _generate_reference(telegram_id: int, plan: str) -> str:
    """Generate a unique Paystack reference."""
    ts = int(datetime.now(timezone.utc).timestamp())
    return f"FYP-{telegram_id}-{plan}-{ts}"


def _calculate_expiry(plan_key: str) -> str:
    """Calculate subscription expiry date based on plan."""
    days = PLANS.get(plan_key, {}).get("days", 7)
    expiry = datetime.now(timezone.utc) + timedelta(days=days)
    return expiry.isoformat()


def _get_user_email(user: dict) -> str:
    """Get or generate an email for Paystack (requires email)."""
    if user.get("email"):
        return user["email"]
    # Fallback email using telegram ID — Paystack requires a valid email
    return f"user{user['telegram_id']}@fyp-mentor.ng"


# ─── PLAN SELECTION ───────────────────────────────────────────────────────────

async def handle_plan_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """User taps a payment plan button."""
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("pay_", "")
    user_id = query.from_user.id
    print(f"[payments] Plan selected: {plan_key} | user={user_id}")

    plan = PLANS.get(plan_key)
    if not plan:
        await query.message.reply_text("Invalid plan. Please try again.")
        return

    user = get_user(user_id)
    if not user:
        await query.message.reply_text(
            "Could not find your account. Please send /start."
        )
        return

    email     = _get_user_email(user)
    reference = _generate_reference(user_id, plan_key)

    # Create pending payment record
    create_payment_record(
        telegram_id=user_id,
        reference=reference,
        plan=plan_key,
        amount=plan["amount"],
    )

    # Initialize with Paystack
    try:
        await query.edit_message_text(
            f"Creating your payment link for *{plan['name']}* ({plan['naira']})...",
            parse_mode="Markdown",
        )
        result = await _initialize_paystack_transaction(
            email=email,
            amount=plan["amount"],
            reference=reference,
            metadata={
                "telegram_id": user_id,
                "plan":        plan_key,
                "plan_name":   plan["name"],
            },
        )

        if not result.get("status"):
            raise Exception(result.get("message", "Paystack initialization failed"))

        payment_url = result["data"]["authorization_url"]
        print(f"[payments] Payment URL generated for user {user_id}")

        await query.edit_message_text(
            f"💳 *{plan['name']} — {plan['naira']}*\n\n"
            f"Tap the button below to pay securely via Paystack.\n\n"
            f"After payment, tap *'I've paid — check status'* "
            f"and I'll unlock your chapters immediately.\n\n"
            f"_Reference: `{reference}`_",
            parse_mode="Markdown",
            reply_markup=payment_link_keyboard(payment_url),
        )

    except Exception as e:
        print(f"[payments] Plan selection error: {e}")
        await query.message.reply_text(
            "Failed to create payment link. Please try again in a moment.\n\n"
            f"Error: {str(e)[:100]}"
        )


# ─── CHECK PAYMENT STATUS ─────────────────────────────────────────────────────

async def handle_check_payment(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """User taps 'Check payment status' or sends /checkpayment."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        send = query.message.reply_text
    else:
        user_id = update.effective_user.id
        send = update.message.reply_text

    print(f"[payments] check_payment: user={user_id}")

    payment = get_latest_payment(user_id)
    if not payment:
        await send(
            "No payment found for your account.\n\n"
            "If you'd like to subscribe, tap the payment button below:",
            reply_markup=payment_plans_keyboard(),
        )
        return

    reference = payment["paystack_reference"]

    # If already confirmed in DB — just recheck subscription status
    if payment.get("status") == "success":
        await send(
            "✅ *Your payment is confirmed!*\n\n"
            "Your subscription is active. "
            "Send /start to continue your project.",
            parse_mode="Markdown",
        )
        return

    # Verify with Paystack
    await send("Checking your payment status with Paystack...")

    try:
        result = await _verify_paystack_transaction(reference)
        tx_data = result.get("data", {})
        status  = tx_data.get("status", "")
        print(f"[payments] Paystack verify result: {status}")

        if status == "success":
            await _grant_access(
                user_id=user_id,
                reference=reference,
                plan_key=payment["plan"],
                send=send,
            )
        elif status == "pending":
            await send(
                "⏳ Your payment is still being processed by Paystack.\n\n"
                "This usually takes less than a minute. "
                "Please tap *Check payment status* again shortly.",
                parse_mode="Markdown",
                reply_markup=payment_link_keyboard(""),
            )
        else:
            await send(
                f"❌ Payment not confirmed. Status: *{status}*\n\n"
                "Please try paying again or contact support.",
                parse_mode="Markdown",
                reply_markup=payment_plans_keyboard(),
            )

    except Exception as e:
        print(f"[payments] check_payment verify error: {e}")
        await send(
            "Could not verify payment right now. Please try again in a moment.\n"
            "Use /checkpayment to retry."
        )


async def _grant_access(
    user_id: int,
    reference: str,
    plan_key: str,
    send,
) -> None:
    """Grant subscription access after successful payment verification."""
    print(f"[payments] _grant_access: user={user_id} plan={plan_key}")
    expires_at = _calculate_expiry(plan_key)
    plan = PLANS.get(plan_key, {})

    # Update payment record
    confirm_payment(reference, expires_at)

    # Update user subscription
    update_user(user_id, {
        "subscription_status":     "active",
        "subscription_plan":       plan_key,
        "subscription_expires_at": expires_at,
    })

    print(f"[payments] Access granted to user {user_id} until {expires_at}")

    await send(
        f"🎉 *Payment confirmed! Welcome to {plan.get('name', 'FYP Mentor')}!*\n\n"
        f"Your subscription is now active.\n\n"
        f"You now have access to Chapters 3, 4, and 5.\n\n"
        f"Tap the button below to continue your project:",
        parse_mode="Markdown",
        reply_markup=_continue_keyboard(user_id),
    )


def _continue_keyboard(user_id: int):
    """Build a keyboard pointing to the student's next chapter."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    project = get_active_project(user_id)
    next_ch = 3
    if project:
        done = project.get("chapters_completed", 0)
        next_ch = max(3, done + 1)
        next_ch = min(next_ch, 5)

    from utils.constants import CHAPTER_NAMES
    name = CHAPTER_NAMES.get(next_ch, f"Chapter {next_ch}")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"Continue — Chapter {next_ch}: {name}",
            callback_data=f"gen_chapter_{next_ch}",
        )
    ]])


# ─── PAYSTACK WEBHOOK (called from FastAPI in main.py) ────────────────────────

async def process_paystack_webhook(
    payload: bytes,
    signature: str,
    bot,
) -> bool:
    """
    Process a Paystack webhook event.
    Called from the FastAPI webhook endpoint in main.py.

    Returns True if processed successfully, False otherwise.
    """
    print(f"[payments] process_paystack_webhook called")

    # ── Verify HMAC-SHA512 signature ──────────────────────────────────────────
    if not _verify_webhook_signature(payload, signature):
        print(f"[payments] Webhook signature verification FAILED")
        return False

    try:
        event = json.loads(payload)
        event_type = event.get("event", "")
        print(f"[payments] Webhook event type: {event_type}")

        if event_type == "charge.success":
            await _handle_charge_success(event["data"], bot)
            return True

        if event_type == "invoice.payment_failed":
            await _handle_payment_failed(event["data"], bot)
            return True

        print(f"[payments] Unhandled webhook event: {event_type}")
        return True

    except Exception as e:
        print(f"[payments] Webhook processing error: {e}")
        return False


def _verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Paystack webhook HMAC-SHA512 signature."""
    print("[payments] Verifying webhook signature...")
    try:
        expected = hmac.new(
            PAYSTACK_WEBHOOK_SECRET.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha512,
        ).hexdigest()
        result = hmac.compare_digest(expected, signature)
        print(f"[payments] Signature valid: {result}")
        return result
    except Exception as e:
        print(f"[payments] Signature verification error: {e}")
        return False


async def _handle_charge_success(data: dict, bot) -> None:
    """Handle a successful charge webhook from Paystack."""
    reference = data.get("reference", "")
    print(f"[payments] charge.success: ref={reference}")

    payment = get_payment_by_reference(reference)
    if not payment:
        print(f"[payments] No payment record found for ref={reference}")
        return

    if payment.get("status") == "success":
        print(f"[payments] Payment already confirmed: {reference}")
        return

    user_id  = payment["telegram_id"]
    plan_key = payment["plan"]
    plan     = PLANS.get(plan_key, {})
    expires_at = _calculate_expiry(plan_key)

    # Confirm in DB
    confirm_payment(reference, expires_at)
    update_user(user_id, {
        "subscription_status":     "active",
        "subscription_plan":       plan_key,
        "subscription_expires_at": expires_at,
    })

    # DM the student
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 *Payment confirmed!*\n\n"
                f"Your *{plan.get('name', 'subscription')}* is now active.\n\n"
                f"You can now generate Chapters 3, 4, and 5.\n\n"
                f"Send /start to continue your project."
            ),
            parse_mode="Markdown",
        )
        print(f"[payments] DM sent to user {user_id} confirming payment")
    except Exception as e:
        print(f"[payments] Failed to DM user {user_id}: {e}")


async def _handle_payment_failed(data: dict, bot) -> None:
    """Handle a failed payment webhook — DM the student with a renewal link."""
    reference = data.get("reference", "")
    print(f"[payments] invoice.payment_failed: ref={reference}")

    payment = get_payment_by_reference(reference)
    if not payment:
        return

    user_id = payment["telegram_id"]
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "⚠️ *Payment failed*\n\n"
                "Your payment could not be processed. "
                "Paystack does not retry failed payments automatically.\n\n"
                "Please try again using /subscribe.",
            ),
            parse_mode="Markdown",
            reply_markup=payment_plans_keyboard(),
        )
        print(f"[payments] Failed payment DM sent to user {user_id}")
    except Exception as e:
        print(f"[payments] Failed to DM user {user_id} about failed payment: {e}")


# ─── COMMANDS ─────────────────────────────────────────────────────────────────

async def handle_subscribe_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/subscribe command — show payment plans."""
    user_id = update.effective_user.id
    print(f"[payments] /subscribe command: user={user_id}")
    await update.message.reply_text(
        format_paywall_message(),
        parse_mode="Markdown",
        reply_markup=payment_plans_keyboard(),
    )


async def handle_checkpayment_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/checkpayment command — manually verify latest payment."""
    print(f"[payments] /checkpayment command: user={update.effective_user.id}")
    await handle_check_payment(update, context)


# ─── HANDLER REGISTRATION ─────────────────────────────────────────────────────

def register_payment_handlers(application) -> None:
    """Register all payment-related handlers."""
    print("[payments] Registering payment handlers...")

    application.add_handler(
        CallbackQueryHandler(handle_plan_selection, pattern="^pay_")
    )
    application.add_handler(
        CallbackQueryHandler(handle_check_payment, pattern="^check_payment$")
    )
    application.add_handler(
        CommandHandler("subscribe", handle_subscribe_command)
    )
    application.add_handler(
        CommandHandler("checkpayment", handle_checkpayment_command)
    )

    print("[payments] Payment handlers registered.")


print("[payments.py] Payments handler loaded.")