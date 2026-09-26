"""
app/services/whatsapp_voice.py

Spoken audio note generator for WhatsApp voice notes (Phase 4).
Uses gTTS (Google Text-to-Speech) to generate English and Afrikaans audio MP3
files for WhatsApp delivery.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parents[2] / "uploads" / "audio"


def generate_spoken_audio(text: str, lang: str = "en") -> str:
    """
    Generates an MP3 audio file for the given alert text and language.
    Returns the relative static URL path (e.g. '/static/audio/alert_abc123.mp3').
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex[:12]
    filename = f"alert_{file_id}.mp3"
    filepath = AUDIO_DIR / filename

    clean_lang = "af" if lang and "af" in lang.lower() else "en"

    try:
        from gtts import gTTS

        tts = gTTS(text=text, lang=clean_lang, slow=False)
        tts.save(str(filepath))
    except Exception as e:
        # Fallback empty audio file if offline / network issues
        with open(filepath, "wb") as f:
            f.write(b"ID3\x04\x00\x00\x00\x00\x00\x00")

    return f"/static/audio/{filename}"


def build_spoken_alert_message(field_name: str, risk_score: str, reasons: list[str], place_name: str = "Patensie") -> str:
    """
    Creates a simple, spoken-language-natural alert prompt for farmers:
    e.g. "Your field near Patensie: some plants may need water soon. Please go and check the north side."
    """
    if risk_score.lower() == "low":
        return f"Your field near {place_name} is looking healthy. All moisture and temperature levels are normal today."

    reasons_text = ". ".join(reasons) if reasons else "moisture levels are dropping"
    return (
        f"Your field near {place_name}: {risk_score} risk alert. {reasons_text}. "
        f"Please go and check your field today."
    )
