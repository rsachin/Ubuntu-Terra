import { useState, useRef } from "react";
import { SpeakerIcon, InfoIcon, PlayIcon } from "./Icons";
import { DISCLAIMER_TEXT } from "./DisclaimerModal";

export default function AlertPreview({ alerts }) {
  const [language, setLanguage] = useState("en");
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const audioRef = useRef(null);

  const latest = alerts?.[0];
  const message = latest
    ? translateAlertMessage(latest.message, language)
    : null;

  const replayDisclaimerSpeech = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const text = DISCLAIMER_TEXT[language] || DISCLAIMER_TEXT.en;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = TTS_LANG[language] || TTS_LANG.en;
    window.speechSynthesis.speak(utterance);
  };

  const toggleAudioPlay = () => {
    if (!audioRef.current) return;
    if (isPlayingAudio) {
      audioRef.current.pause();
      setIsPlayingAudio(false);
    } else {
      audioRef.current
        .play()
        .then(() => setIsPlayingAudio(true))
        .catch(() => setIsPlayingAudio(false));
    }
  };

  return (
    <section className="panel">
      <div className="panel__header panel__header--stacked">
        <div>
          <h2>WhatsApp Voice Alert Preview</h2>
          <p className="panel__hint">
            Off-platform WhatsApp Business Sandbox delivery simulated for farmers
          </p>
        </div>
        <div
          className="field-list-filters"
          aria-label="Toggle alert language"
        >
          <button
            type="button"
            className={`field-filter-btn${language === "en" ? " is-active" : ""}`}
            onClick={() => setLanguage("en")}
          >
            EN
          </button>
          <button
            type="button"
            className={`field-filter-btn${language === "af" ? " is-active" : ""}`}
            onClick={() => setLanguage("af")}
          >
            AF
          </button>
          <button
            type="button"
            className={`field-filter-btn${language === "zu" ? " is-active" : ""}`}
            onClick={() => setLanguage("zu")}
          >
            ZU
          </button>
          <button
            type="button"
            className={`field-filter-btn${language === "nso" ? " is-active" : ""}`}
            onClick={() => setLanguage("nso")}
          >
            NSO
          </button>
        </div>
      </div>

      {/* First-Use Disclaimer Box inside card */}
      <div className="alert-disclaimer-card">
        <div className="alert-disclaimer-card__icon">
          <SpeakerIcon size={22} />
        </div>
        <p className="alert-disclaimer-card__text">
          {DISCLAIMER_TEXT[language] || DISCLAIMER_TEXT.en}
        </p>
        <button
          type="button"
          className="alert-disclaimer-card__replay-btn"
          onClick={replayDisclaimerSpeech}
          title="Replay spoken disclaimer message"
          aria-label="Replay spoken disclaimer message"
        >
          <InfoIcon size={18} />
        </button>
      </div>

      {!latest ? (
        <p className="panel__empty">No alert generated yet for this field.</p>
      ) : (
        <div
          className="alert-bubble"
          style={{
            background: "rgba(10, 24, 14, 0.85)",
            border: "1px solid rgba(46, 213, 115, 0.25)",
            borderRadius: "16px",
            padding: "16px 18px",
          }}
        >
          <div className="alert-bubble__header">
            <span
              className="alert-bubble__channel"
              style={{
                color: "var(--accent-primary)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                fontWeight: 600,
              }}
            >
              📱 WhatsApp Business Voice Sandbox
            </span>
            <span
              className="alert-bubble__type-badge"
              style={{
                background: "rgba(46, 213, 115, 0.15)",
                color: "var(--accent-primary)",
                border: "1px solid rgba(46, 213, 115, 0.3)",
                fontSize: "0.72rem",
                padding: "2px 8px",
                borderRadius: "999px",
              }}
            >
              Text + Voice Note
            </span>
          </div>

          <p
            className="alert-bubble__text"
            style={{
              color: "#fff",
              fontSize: "0.92rem",
              lineHeight: 1.5,
              margin: "10px 0 14px",
            }}
          >
            {message}
          </p>

          {/* WhatsApp Voice Note Preview using Waveform Pill pattern */}
          {latest.audio_url && (
            <div style={{ margin: "14px 0" }}>
              <div
                className="waveform-pill-btn"
                style={{
                  cursor: "pointer",
                  background: "rgba(0, 0, 0, 0.4)",
                  borderColor: "rgba(46, 213, 115, 0.3)",
                }}
                onClick={toggleAudioPlay}
              >
                <div className="waveform-pill-btn__left">
                  <button
                    type="button"
                    style={{
                      background: "var(--accent-primary)",
                      border: "none",
                      borderRadius: "50%",
                      width: "28px",
                      height: "28px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <PlayIcon size={12} color="#0a140c" />
                  </button>
                  <span style={{ fontSize: "0.82rem", fontWeight: 600 }}>
                    {isPlayingAudio ? "Playing Voice Note…" : "🎙️ WhatsApp Voice Note (0:14)"}
                  </span>
                </div>

                <div className={`waveform-graphic${isPlayingAudio ? " is-playing" : ""}`}>
                  <span className="waveform-bar waveform-bar--cyan" style={{ height: "10px" }} />
                  <span className="waveform-bar waveform-bar--green" style={{ height: "14px" }} />
                  <span className="waveform-bar waveform-bar--amber" style={{ height: "7px" }} />
                  <span className="waveform-bar waveform-bar--red" style={{ height: "12px" }} />
                  <span className="waveform-bar waveform-bar--cyan" style={{ height: "9px" }} />
                  <span className="waveform-bar waveform-bar--green" style={{ height: "16px" }} />
                  <span className="waveform-bar waveform-bar--amber" style={{ height: "5px" }} />
                </div>
              </div>
              <audio
                ref={audioRef}
                src={latest.audio_url}
                onEnded={() => setIsPlayingAudio(false)}
                style={{ display: "none" }}
              />
            </div>
          )}

          <div
            className="alert-whatsapp-replies"
            style={{
              marginTop: "12px",
              paddingTop: "10px",
              borderTop: "1px dashed rgba(255,255,255,0.1)",
            }}
          >
            <span style={{ fontSize: "0.78rem", color: "var(--ink-soft)" }}>
              Farmer WhatsApp Interactive Replies:
            </span>
            <div className="alert-reply-tags" style={{ marginTop: "6px" }}>
              <span className="reply-tag" style={{ color: "var(--accent-primary)" }}>
                Reply "YES" / "JA" / "YEBO" / "EE" (Confirm)
              </span>
              <span className="reply-tag" style={{ color: "var(--accent-low)" }}>
                Reply "MORE INFO" / "LUSISI" (Explain)
              </span>
            </div>
          </div>

          <time
            className="alert-bubble__time"
            style={{
              display: "block",
              marginTop: "10px",
              fontSize: "0.72rem",
              color: "var(--ink-muted)",
            }}
          >
            {formatTime(latest.created_at)}
          </time>
        </div>
      )}
    </section>
  );
}

const TTS_LANG = {
  en: "en-US",
  af: "af-ZA",
  zu: "zu-ZA",
  nso: "nso-ZA",
};

function translateAlertMessage(message, language) {
  if (language === "en") return message;
  if (language === "af") return translateToAfrikaans(message);
  if (language === "zu") return translateToZulu(message);
  if (language === "nso") return translateToSepedi(message);
  return message;
}

function translateToAfrikaans(message) {
  return message
    .replace(/low risk/gi, "lae risiko")
    .replace(/medium risk/gi, "matige risiko")
    .replace(/high risk/gi, "hoë risiko")
    .replace(/no action needed/gi, "geen aksie nodig")
    .replace(
      /check the irrigation system/gi,
      "kontroleer die besproeiingstelsel",
    )
    .replace(/check for heat stress/gi, "kontroleer hitte-stres")
    .replace(/conditions normal/gi, "toestande is normaal");
}

function translateToZulu(message) {
  return message
    .replace(/low risk/gi, "ingozi encane")
    .replace(/medium risk/gi, "ingozi engxenyana")
    .replace(/high risk/gi, "ingozi enkulu")
    .replace(/no action needed/gi, "akukenziwa lutho")
    .replace(
      /check the irrigation system/gi,
      "hlola uhlelo lokunisela",
    )
    .replace(/check for heat stress/gi, "hlola ukushiswa kwentuthuko")
    .replace(/conditions normal/gi, "izimo zijwayelekile");
}

function translateToSepedi(message) {
  return message
    .replace(/low risk/gi, "kotsi ya tlase")
    .replace(/medium risk/gi, "kotsi ya magareng")
    .replace(/high risk/gi, "kotsi yeo e lego godimo")
    .replace(/no action needed/gi, "ga go nyakege tirelo")
    .replace(
      /check the irrigation system/gi,
      "hlola tshepedišo ya go nokela",
    )
    .replace(/check for heat stress/gi, "hlola kgatelelo ya go mona")
    .replace(/conditions normal/gi, "maemo a a tlwaelegilego");
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
