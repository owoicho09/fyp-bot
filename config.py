print("[config.py] Loading and validating all environment variables...")

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Crash loudly if a required environment variable is missing."""
    val = os.getenv(key, "").strip()
    if not val:
        raise EnvironmentError(
            f"\n\n[config.py] FATAL ERROR: '{key}' is missing from your .env file.\n"
            f"The bot cannot start without this. Add it and restart.\n"
        )
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")

# ── OpenAI (Whisper transcription only) ───────────────────────────────────────
OPENAI_API_KEY = _require("OPENAI_API_KEY")

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = _require("SUPABASE_URL")
SUPABASE_KEY = _require("SUPABASE_KEY")

# ── Paystack ──────────────────────────────────────────────────────────────────
PAYSTACK_SECRET_KEY    = _require("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY    = _require("PAYSTACK_PUBLIC_KEY")
PAYSTACK_WEBHOOK_SECRET = _require("PAYSTACK_WEBHOOK_SECRET")

# ── App ───────────────────────────────────────────────────────────────────────
WEBHOOK_URL = _optional("WEBHOOK_URL")          # empty in dev, set on Railway
APP_ENV     = _optional("APP_ENV", "development")
PORT        = int(_optional("PORT", "8000"))
IS_PROD     = APP_ENV == "production"

# ── Claude model routing ──────────────────────────────────────────────────────
# Sonnet for Chapter 2 (citation-heavy literature review — needs best reasoning)
# Sonnet also for the intake agent (needs to reason about research design)
# Haiku for all other chapters (fast + cheap, quality still excellent)
MODEL_INTAKE    = "claude-sonnet-4-5"
MODEL_CHAPTER_2 = "claude-sonnet-4-5"
MODEL_DEFAULT   = "claude-haiku-4-5-20251001"

# ── Paystack subscription plans ───────────────────────────────────────────────
# Amounts in kobo (1 naira = 100 kobo)
PLANS = {
    "weekly": {
        "name":   "Weekly Pass",
        "amount": 300_000,        # ₦1,000
        "naira":  "₦3,000",
        "label":  "₦3,000 / week — Chapters 3, 4 & 5 + all tools",
        "days":   7,
    },
    "project": {
        "name":   "Project Pass",
        "amount": 750_000,        # ₦4,500
        "naira":  "₦7,500",
        "label":  "₦7,500 one-time — All chapters + 90 days (best value)",
        "days":   90,
    },
    "postgrad": {
        "name":   "Postgrad Pass",
        "amount": 1000_000,        # ₦8,000
        "naira":  "₦10,000",
        "label":  "₦10,000 / month — MSc/MBA format + extended support",
        "days":   30,
    },
}

print(
    f"[config.py] Configuration loaded.\n"
    f"  Environment : {APP_ENV}\n"
    f"  Port        : {PORT}\n"
    f"  Webhook URL : {WEBHOOK_URL or '(not set — running in polling mode)'}\n"
    f"  Intake model: {MODEL_INTAKE}\n"
    f"  Default model: {MODEL_DEFAULT}\n"
)