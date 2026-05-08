print("[whisper_service.py] Loading Whisper transcription service...")

import os
import tempfile
import aiofiles
from openai import AsyncOpenAI
from telegram import Bot
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
print("[whisper_service.py] OpenAI async client ready.")


# ─── SUPPORTED VOICE MIME TYPES FROM TELEGRAM ────────────────────────────────
# Telegram sends voice notes as OGG/OPUS.
# Whisper accepts: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg
SUPPORTED_EXTENSIONS = {
    "audio/ogg":  ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4":  ".mp4",
    "audio/wav":  ".wav",
    "audio/webm": ".webm",
}
DEFAULT_EXTENSION = ".ogg"


async def transcribe_voice_message(bot: Bot, file_id: str) -> dict:
    """
    Download a Telegram voice note and transcribe it with OpenAI Whisper.

    Returns a dict:
        {
            "success": True,
            "transcript": "the transcribed text...",
            "duration_seconds": 12,
        }
    or on failure:
        {
            "success": False,
            "error": "reason",
        }
    """
    print(f"[whisper] transcribe_voice_message called. file_id={file_id[:20]}...")

    # ── Step 1: Get file info from Telegram ───────────────────────────────────
    try:
        print("[whisper] Fetching file info from Telegram...")
        tg_file = await bot.get_file(file_id)
        file_path = tg_file.file_path
        print(f"[whisper] Telegram file path: {file_path}")
    except Exception as e:
        print(f"[whisper] ERROR fetching file info: {e}")
        return {"success": False, "error": f"Could not fetch voice file from Telegram: {e}"}

    # ── Step 2: Download audio bytes ──────────────────────────────────────────
    try:
        print("[whisper] Downloading audio bytes from Telegram...")
        audio_bytes = await tg_file.download_as_bytearray()
        print(f"[whisper] Downloaded {len(audio_bytes)} bytes.")
    except Exception as e:
        print(f"[whisper] ERROR downloading audio: {e}")
        return {"success": False, "error": f"Could not download voice file: {e}"}

    # ── Step 3: Write to a temp file and send to Whisper ─────────────────────
    # Whisper API requires a real file object with a name — not raw bytes.
    # We write to a named temp file so the file extension is preserved.
    tmp_path = None
    try:
        print("[whisper] Writing audio to temp file...")
        with tempfile.NamedTemporaryFile(
            suffix=DEFAULT_EXTENSION,
            delete=False,
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        print(f"[whisper] Temp file written: {tmp_path}")

        print("[whisper] Sending to OpenAI Whisper API...")
        with open(tmp_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en",          # English first — Whisper auto-detects if wrong
                response_format="text", # Plain text, no timestamps needed
            )

        transcript = response.strip() if isinstance(response, str) else str(response).strip()
        print(f"[whisper] Transcription successful. Length: {len(transcript)} chars.")
        print(f"[whisper] Preview: {transcript[:100]}...")

        return {
            "success":          True,
            "transcript":       transcript,
            "duration_seconds": None,   # Telegram voice objects include duration — passed separately
        }

    except Exception as e:
        print(f"[whisper] ERROR during Whisper transcription: {e}")
        return {"success": False, "error": f"Transcription failed: {e}"}

    finally:
        # ── Step 4: Always clean up the temp file ─────────────────────────────
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                print(f"[whisper] Temp file deleted: {tmp_path}")
            except Exception as e:
                print(f"[whisper] WARNING: Could not delete temp file {tmp_path}: {e}")


async def transcribe_audio_file(file_path: str) -> dict:
    """
    Transcribe an audio file already on disk.
    Used for testing or if audio is saved locally before processing.
    """
    print(f"[whisper] transcribe_audio_file called. path={file_path}")
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        with open(file_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en",
                response_format="text",
            )
        transcript = response.strip() if isinstance(response, str) else str(response).strip()
        print(f"[whisper] File transcription done. Length: {len(transcript)}")
        return {"success": True, "transcript": transcript}
    except Exception as e:
        print(f"[whisper] ERROR: {e}")
        return {"success": False, "error": str(e)}


def build_voice_received_message(duration: int = None) -> str:
    """
    Message shown to the student immediately after receiving their voice note,
    while transcription is happening in the background.
    """
    duration_text = f" ({duration}s)" if duration else ""
    return (
        f"🎙️ Voice note received{duration_text}. Transcribing...\n\n"
        "Please wait a moment."
    )


def build_transcription_preview(transcript: str) -> str:
    """
    Show the student what was transcribed so they can confirm or correct it.
    """
    print("[whisper] build_transcription_preview called")
    preview = transcript[:300] + "..." if len(transcript) > 300 else transcript
    return (
        f"✅ *I heard:*\n\n"
        f"_{preview}_\n\n"
        "Processing your response..."
    )


print("[whisper_service.py] Whisper service loaded.")