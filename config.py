print("[config.py] Loading and validating all environment variables...")

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
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

# ── App ───────────────────────────────────────────────────────────────────────
WEBHOOK_URL = _optional("WEBHOOK_URL")
APP_ENV     = _optional("APP_ENV", "development")
PORT        = int(_optional("PORT", "8000"))
IS_PROD     = APP_ENV == "production"

# ── Claude model routing ──────────────────────────────────────────────────────
MODEL_INTAKE    = "claude-sonnet-4-5"
MODEL_CHAPTER_2 = "claude-sonnet-4-5"
MODEL_DEFAULT   = "claude-haiku-4-5-20251001"

# ── Telegram Stars payment plans ─────────────────────────────────────────────
# 1 Star ≈ ₦50 at current Telegram rate
# Prices shown to students in Naira — Stars shown as secondary info
PLANS = {
    "weekly": {
        "name":        "Weekly Pass",
        "stars":       60,           # 60 Stars ≈ ₦3,000
        "naira":       "₦3,000",
        "label":       "₦3,000/week — Chapters 3, 4 & 5 + all tools",
        "description": "7-day access to all chapters, voice notes, corrections and PDF download",
        "days":        7,
    },
    "project": {
        "name":        "Project Pass",
        "stars":       200,          # 200 Stars ≈ ₦10,000
        "naira":       "₦10,000",
        "label":       "₦10,000 one-time — All chapters + 90 days (best value ⭐)",
        "description": "90-day access to all chapters, unlimited corrections and document download",
        "days":        90,
    },
    "postgrad": {
        "name":        "Postgrad Pass",
        "stars":       200,          # 200 Stars ≈ ₦10,000
        "naira":       "₦10,000",
        "label":       "₦10,000/month — MSc/MBA/PhD format + extended support",
        "description": "30-day postgraduate access with MSc/MBA format, contributions to knowledge section",
        "days":        30,
    },
}

print(
    f"[config.py] Configuration loaded.\n"
    f"  Environment : {APP_ENV}\n"
    f"  Port        : {PORT}\n"
    f"  Webhook URL : {WEBHOOK_URL or '(not set — polling mode)'}\n"
    f"  Models      : intake={MODEL_INTAKE} default={MODEL_DEFAULT}\n"
    f"  Payment     : Telegram Stars\n"
)