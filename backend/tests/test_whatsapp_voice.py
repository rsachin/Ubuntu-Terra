"""
Tests for services/whatsapp_voice.py — no database required.

Covers the language fallback logic: gTTS 2.5.4 only supports English and
Afrikaans, so Zulu and Sepedi requests must fall back to English audio while
keeping the text alert in the requested language.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.whatsapp_voice import generate_spoken_audio


def test_generate_spoken_audio_uses_english_for_english():
    with patch("app.services.whatsapp_voice.AUDIO_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_path = MagicMock(spec=Path)
        mock_dir.__truediv__.return_value = mock_path
        mock_path.__str__.return_value = "/tmp/alert_en.mp3"

        with patch("gtts.gTTS") as mock_tts:
            generate_spoken_audio("test message", lang="en")
            assert mock_tts.call_args.kwargs["lang"] == "en"


def test_generate_spoken_audio_uses_afrikaans_for_afrikaans():
    with patch("app.services.whatsapp_voice.AUDIO_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_path = MagicMock(spec=Path)
        mock_dir.__truediv__.return_value = mock_path
        mock_path.__str__.return_value = "/tmp/alert_af.mp3"

        with patch("gtts.gTTS") as mock_tts:
            generate_spoken_audio("test message", lang="af")
            assert mock_tts.call_args.kwargs["lang"] == "af"


def test_generate_spoken_audio_falls_back_to_english_for_zulu():
    with patch("app.services.whatsapp_voice.AUDIO_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_path = MagicMock(spec=Path)
        mock_dir.__truediv__.return_value = mock_path
        mock_path.__str__.return_value = "/tmp/alert_zu.mp3"

        with patch("gtts.gTTS") as mock_tts:
            generate_spoken_audio("test message", lang="zu")
            assert mock_tts.call_args.kwargs["lang"] == "en"


def test_generate_spoken_audio_falls_back_to_english_for_sepedi():
    with patch("app.services.whatsapp_voice.AUDIO_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_path = MagicMock(spec=Path)
        mock_dir.__truediv__.return_value = mock_path
        mock_path.__str__.return_value = "/tmp/alert_nso.mp3"

        with patch("gtts.gTTS") as mock_tts:
            generate_spoken_audio("test message", lang="nso")
            assert mock_tts.call_args.kwargs["lang"] == "en"
