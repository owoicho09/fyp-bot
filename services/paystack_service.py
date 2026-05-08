print("[paystack_service.py] Loading Paystack service...")

import hmac
import hashlib
import httpx
from datetime import datetime, timezone, timedelta
from config import PAYSTACK_SECRET_KEY, PAYSTACK_WEBHOOK_SECRET, PLANS


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

INIT_URL   = "https://api.paystack.co/transaction/initialize"
VERIFY_URL = "https://api.paystack.co/transaction/verify"


# ─── TRANSACTION INITIALIZE ───────────────────────────────────────────────────

async def initialize_transaction(
    email: str,
    amount: int,
    reference: str,
    telegram_id: int,
    plan_key: str,
) -> dict:
    """
    Initialize a Paystack transaction.
    Returns the authorization URL for the student to pay on.

    Args:
        email:       Student email (real or generated fallback)
        amount:      Amount in kobo (naira × 100)
        reference:   Unique transaction reference
        telegram_id: Student's Telegram ID (stored in metadata)
        plan_key:    Plan key from PLANS dict

    Returns:
        {
            "success":       True | False,
            "payment_url":   "https://checkout.paystack.com/...",
            "reference":     "FYP-...",
            "error":         "error message if failed",
        }
    """
    print(f"[paystack] initialize_transaction: ref={reference} amount={amount} plan={plan_key}")

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "email":        email,
        "amount":       amount,
        "reference":    reference,
        "metadata": {
            "telegram_id": telegram_id,
            "plan":        plan_key,
            "plan_name":   PLANS.get(plan_key, {}).get("name", ""),
            "custom_fields": [
                {
                    "display_name": "Telegram ID",
                    "variable_name": "telegram_id",
                    "value": str(telegram_id),
                },
                {
                    "display_name": "Plan",
                    "variable_name": "plan",
                    "value": plan_key,
                },
            ],
        },
        "callback_url": "https://t.me/FYPMentorBot",
        "channels":     ["card", "bank", "ussd", "mobile_money", "bank_transfer"],
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(INIT_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if not data.get("status"):
            print(f"[paystack] Init failed: {data.get('message')}")
            return {
                "success":     False,
                "payment_url": "",
                "reference":   reference,
                "error":       data.get("message", "Initialization failed"),
            }

        payment_url = data["data"]["authorization_url"]
        print(f"[paystack] Transaction initialized. URL: {payment_url[:60]}...")
        return {
            "success":     True,
            "payment_url": payment_url,
            "reference":   reference,
            "error":       "",
        }

    except httpx.TimeoutException:
        print("[paystack] initialize_transaction TIMEOUT")
        return {
            "success":     False,
            "payment_url": "",
            "reference":   reference,
            "error":       "Request timed out. Please try again.",
        }
    except Exception as e:
        print(f"[paystack] initialize_transaction ERROR: {e}")
        return {
            "success":     False,
            "payment_url": "",
            "reference":   reference,
            "error":       str(e),
        }


# ─── TRANSACTION VERIFY ───────────────────────────────────────────────────────

async def verify_transaction(reference: str) -> dict:
    """
    Verify a transaction with Paystack.

    Returns:
        {
            "success":   True | False,
            "status":    "success" | "pending" | "failed" | "abandoned",
            "amount":    amount paid in kobo,
            "email":     customer email,
            "plan":      plan_key from metadata,
            "telegram_id": telegram_id from metadata,
            "error":     "error message if request failed",
        }
    """
    print(f"[paystack] verify_transaction: ref={reference}")

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{VERIFY_URL}/{reference}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        tx = data.get("data", {})
        status = tx.get("status", "unknown")
        print(f"[paystack] Verify result: status={status}")

        # Extract metadata
        metadata    = tx.get("metadata", {}) or {}
        telegram_id = metadata.get("telegram_id")
        plan_key    = metadata.get("plan", "")

        # Fallback — try custom_fields
        if not telegram_id:
            for field in metadata.get("custom_fields", []):
                if field.get("variable_name") == "telegram_id":
                    telegram_id = int(field.get("value", 0))
                if field.get("variable_name") == "plan":
                    plan_key = field.get("value", "")

        return {
            "success":     data.get("status", False),
            "status":      status,
            "amount":      tx.get("amount", 0),
            "email":       tx.get("customer", {}).get("email", ""),
            "plan":        plan_key,
            "telegram_id": int(telegram_id) if telegram_id else None,
            "error":       "",
        }

    except httpx.TimeoutException:
        print("[paystack] verify_transaction TIMEOUT")
        return {
            "success":     False,
            "status":      "unknown",
            "amount":      0,
            "email":       "",
            "plan":        "",
            "telegram_id": None,
            "error":       "Verification timed out. Use /checkpayment to retry.",
        }
    except Exception as e:
        print(f"[paystack] verify_transaction ERROR: {e}")
        return {
            "success":     False,
            "status":      "unknown",
            "amount":      0,
            "email":       "",
            "plan":        "",
            "telegram_id": None,
            "error":       str(e),
        }


# ─── WEBHOOK SIGNATURE VERIFICATION ──────────────────────────────────────────

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify Paystack webhook HMAC-SHA512 signature.
    Paystack signs every webhook with your secret key.
    Never process a webhook without verifying this first.
    """
    print("[paystack] verify_webhook_signature called")
    try:
        expected = hmac.new(
            PAYSTACK_WEBHOOK_SECRET.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha512,
        ).hexdigest()
        result = hmac.compare_digest(expected, signature)
        print(f"[paystack] Signature valid: {result}")
        return result
    except Exception as e:
        print(f"[paystack] Signature error: {e}")
        return False


# ─── REFERENCE GENERATOR ─────────────────────────────────────────────────────

def generate_reference(telegram_id: int, plan_key: str) -> str:
    """Generate a unique Paystack transaction reference."""
    ts = int(datetime.now(timezone.utc).timestamp())
    return f"FYP-{telegram_id}-{plan_key}-{ts}"


# ─── EXPIRY CALCULATOR ────────────────────────────────────────────────────────

def calculate_expiry(plan_key: str) -> str:
    """Calculate subscription expiry datetime string for a given plan."""
    days   = PLANS.get(plan_key, {}).get("days", 7)
    expiry = datetime.now(timezone.utc) + timedelta(days=days)
    return expiry.isoformat()


# ─── EMAIL FALLBACK ───────────────────────────────────────────────────────────

def get_or_generate_email(user: dict) -> str:
    """
    Paystack requires an email for every transaction.
    Use the user's real email if stored, otherwise generate a
    deterministic fallback that won't bounce Paystack's validation.
    """
    if user and user.get("email"):
        return user["email"]
    telegram_id = user.get("telegram_id", "unknown") if user else "unknown"
    return f"user{telegram_id}@fyp-mentor.ng"


print("[paystack_service.py] Paystack service loaded.")