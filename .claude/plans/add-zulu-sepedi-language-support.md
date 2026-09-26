# Plan: Add Zulu and Sepedi Language Support

## Goal
Extend Ubuntu Terra's existing English/Afrikaans language support to include **Zulu (zu)** and **Sepedi / Northern Sotho (nso)** across the frontend UI text, spoken read-aloud, and WhatsApp alert pipeline.

## Background
The app currently supports two languages:
- Frontend: `DisclaimerModal.jsx`, `AlertPreview.jsx`, `ConditionPanel.jsx`
- Backend TTS: `whatsapp_voice.py` via gTTS
- Backend WhatsApp replies: `routers/fields.py` webhook

## Limitation Discovered
The installed `gTTS==2.5.4` does **not** list `zu` (Zulu) or `nso` (Sepedi/Northern Sotho) in its supported language map. Therefore:
- Text/UI translations for Zulu and Sepedi will be added fully.
- WhatsApp voice notes for `zu`/`nso` will fall back to English audio while keeping the chosen-language text alert.
- Spoken read-aloud in the browser (`speechSynthesis`) will still set the BCP-47 language tag so any installed voice is selected if available; otherwise the browser falls back to its default voice.

## Files to Change

### Frontend
1. **`frontend/src/components/DisclaimerModal.jsx`**
   - Add `zu` and `nso` entries to `DISCLAIMER_TEXT` with appropriate translations.

2. **`frontend/src/components/AlertPreview.jsx`**
   - Add `zu` and `nso` language toggle buttons.
   - Add `translateToZulu(message)` and `translateToSepedi(message)` helpers mirroring the existing Afrikaans helper.
   - Update `replayDisclaimerSpeech` to use the correct `utterance.lang` per language.

3. **`frontend/src/components/ConditionPanel.jsx`**
   - Replace the two-language toggle with a four-language cycle (EN → AF → ZU → NSO → EN) or a small dropdown/button group.
   - Update `utterance.lang` mapping for TTS to include `zu-ZA` and `nso-ZA`.
   - Keep the same advisory disclaimer read-aloud behaviour.

### Backend
4. **`backend/app/services/whatsapp_voice.py`**
   - Add a `SUPPORTED_GTTS_LANGS = {"en", "af"}` guard.
   - In `generate_spoken_audio`, if the requested `lang` is not supported, fall back to `en` but log a warning so the behaviour is observable.
   - Update module docstring to document the fallback.

5. **`backend/app/routers/fields.py`**
   - Extend the WhatsApp webhook keyword lists to recognise Zulu and Sepedi confirmation/help words:
     - Confirm: `yebo`, `ee` (Zulu/Sepedi yes)
     - Help: `lusisi`, `ncedisa`, `tshedisa`, `ka lebaka` (Zulu/Sepedi explain/help/why)
   - Keep existing English/Afrikaans keywords unchanged.

### Docs / Status
6. **`status.md`**
   - Update the Phase 4 language list to mention Zulu and Sepedi text support and the English fallback for voice notes due to gTTS limitations.

## Testing
- Run the existing backend test suite (`pytest`) to ensure no regressions.
- Verify the new webhook keywords do not break existing `test_whatsapp_webhook.py` assertions (they are additive).
- Manually check the frontend build (`npm run build`) and that the language toggle cycles through all four languages.

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| gTTS throws on unsupported language | Fallback to `en` before instantiating gTTS; log a warning. |
| Web Speech API has no Zulu/Sepedi voice | Set `utterance.lang` anyway; browser falls back to default voice. |
| UI toggle becomes crowded on mobile | Use compact labels (EN / AF / ZU / NSO) in the existing button group. |
| Translations are non-expert | Add a comment that translations are demo-grade and should be reviewed by a native speaker. |

## Out of Scope
- Replacing gTTS with a TTS engine that supports Zulu/Sepedi (post-hackathon).
- Adding a full i18n framework such as react-intl; keep the current lightweight helper pattern.
