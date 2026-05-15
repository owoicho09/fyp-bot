print("[main.py] Starting FYP Mentor bot...")

import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from bot.bot import build_application


# ─── BUILD PTB APPLICATION ────────────────────────────────────────────────────
print("[main.py] Building bot application...")
ptb_app = build_application()


# ─── FASTAPI LIFESPAN ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop the PTB bot alongside FastAPI."""
    print("[main.py] FastAPI lifespan startup...")
    await ptb_app.initialize()

    if IS_PROD and WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook/{TELEGRAM_BOT_TOKEN}"
        await ptb_app.bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query"],
        )
        print(f"[main.py] Webhook set: {webhook_url}")
    else:
        # Development — use polling
        print("[main.py] Development mode — starting polling...")
        await ptb_app.bot.delete_webhook(drop_pending_updates=True)
        await ptb_app.start()
        asyncio.create_task(ptb_app.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        ))
        print("[main.py] Polling started.")

    yield

    print("[main.py] FastAPI lifespan shutdown...")
    if ptb_app.running:
        await ptb_app.stop()
    await ptb_app.shutdown()
    print("[main.py] Bot shut down cleanly.")


# ─── FASTAPI APP ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="FYP Mentor Bot",
    lifespan=lifespan,
)


# ─── TELEGRAM WEBHOOK ENDPOINT ────────────────────────────────────────────────

@app.post(f"/webhook/{TELEGRAM_BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """Receive Telegram updates in production."""
    print("[main.py] Telegram webhook received")
    try:
        data = await request.json()
        from telegram import Update
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        print(f"[main.py] Telegram webhook error: {e}")
        return Response(status_code=500)


# ─── PAYSTACK WEBHOOK ENDPOINT ────────────────────────────────────────────────


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    print("[main.py] Health check called")
    return {
        "status":  "ok",
        "bot":     "FYP Mentor",
        "running": ptb_app.running,
    }


@app.get("/")
async def root():
    return {"message": "FYP Mentor Bot is running."}


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print(f"[main.py] Starting uvicorn on port {PORT}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=not IS_PROD,
        timeout_keep_alive=120,
    )