import { useEffect, useMemo, useState } from "react";
import RiskBadge from "./RiskBadge";
import { DISCLAIMER_TEXT } from "./DisclaimerModal";
import { api } from "../api/client";
import { WaterIcon, HeatIcon, PlantIcon, SpeakerIcon, ChevronDownIcon } from "./Icons";

const TTS_LANG = {
  en: "en-US",
  af: "af-ZA",
  zu: "zu-ZA",
  nso: "nso-ZA",
};

const LANGUAGE_LABELS = {
  en: "English",
  af: "Afrikaans",
  zu: "isiZulu",
  nso: "Sepedi",
};

export default function ConditionPanel({ risk, readings = [], fieldId, fieldName = "Citrus Block", onOpenDisclaimer }) {
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [voiceLanguage, setVoiceLanguage] = useState("en");
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  const [riskFeedbackSaved, setRiskFeedbackSaved] = useState(false);
  const [photoFeedbackSaved, setPhotoFeedbackSaved] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  useEffect(() => {
    setVoiceEnabled(
      typeof window !== "undefined" &&
        "speechSynthesis" in window &&
        "SpeechSynthesisUtterance" in window,
    );
  }, []);

  // Compute dynamic signal status & color coding from risk data
  const signalStates = useMemo(() => {
    if (!risk) return { water: { label: "(normal)", color: "cyan" }, heat: { label: "(normal)", color: "green" }, plant: { label: "(normal)", color: "green" } };

    const score = risk.score;
    const reasonsText = (risk.reasons || []).join(" ").toLowerCase();

    let waterLabel = "(normal)";
    let waterColor = "cyan";
    if (score === "High" || reasonsText.includes("rain") || reasonsText.includes("deficit") || reasonsText.includes("water")) {
      waterLabel = score === "High" ? "(low)" : "(moderate)";
      waterColor = "cyan";
    }

    let heatLabel = "(normal)";
    let heatColor = "green";
    if (reasonsText.includes("heat") || reasonsText.includes("temp") || score === "High") {
      heatLabel = score === "High" ? "(high)" : "(elevated)";
      heatColor = score === "High" ? "red" : "amber";
    }

    let plantLabel = "(normal)";
    let plantColor = "green";
    if (reasonsText.includes("ndvi") || reasonsText.includes("vegetation") || risk.photo_diagnosis) {
      plantLabel = risk.photo_diagnosis ? "(stress)" : "(watch)";
      plantColor = risk.photo_diagnosis ? "amber" : "green";
    }

    return {
      water: { label: waterLabel, color: waterColor },
      heat: { label: heatLabel, color: heatColor },
      plant: { label: plantLabel, color: plantColor },
    };
  }, [risk]);

  if (!risk) {
    return (
      <section className="panel">
        <h2>Field Condition</h2>
        <p className="panel__empty">
          Risk data isn't available for this field right now.
        </p>
      </section>
    );
  }

  const buildAdvisoryText = () => {
    const disclaimer = DISCLAIMER_TEXT[voiceLanguage] || DISCLAIMER_TEXT.en;
    return [
      `Field condition for ${fieldName}.`,
      `Risk level ${risk.score}.`,
      ...risk.reasons,
      `Recommended check: ${risk.recommended_check}.`,
      `Advisory disclaimer: ${disclaimer}`,
    ]
      .filter(Boolean)
      .join(" ");
  };

  const stopSpeaking = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
    setIsPaused(false);
  };

  const togglePauseSpeaking = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
    } else if (window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
      setIsPaused(true);
    }
  };

  const speakRisk = () => {
    if (!voiceEnabled || typeof window === "undefined") return;

    // If already speaking, treat the primary button as a stop control.
    if (isSpeaking) {
      stopSpeaking();
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(buildAdvisoryText());
    utterance.lang = TTS_LANG[voiceLanguage] || TTS_LANG.en;
    utterance.onstart = () => {
      setIsSpeaking(true);
      setIsPaused(false);
    };
    utterance.onend = () => {
      setIsSpeaking(false);
      setIsPaused(false);
    };
    utterance.onerror = () => {
      setIsSpeaking(false);
      setIsPaused(false);
    };
    window.speechSynthesis.speak(utterance);
  };

  const startVoiceQuery = () => {
    if (typeof window === "undefined") return;
    const Recognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) return;

    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript.toLowerCase();
      if (
        transcript.includes("risk") ||
        transcript.includes("check") ||
        transcript.includes("do")
      ) {
        speakRisk();
      }
    };
    recognition.start();
  };

  const handleRiskFeedback = async (wasAccurate) => {
    if (!fieldId || submittingFeedback) return;
    setSubmittingFeedback(true);
    try {
      await api.submitFeedback({
        field_id: fieldId,
        was_accurate: wasAccurate,
        farmer_comment: wasAccurate ? "Farmer confirmed risk assessment" : "Farmer flagged inaccuracy",
      });
      setRiskFeedbackSaved(true);
    } catch {
      // ignore
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const handlePhotoFeedback = async (wasAccurate) => {
    if (!fieldId || !risk.photo_diagnosis || submittingFeedback) return;
    setSubmittingFeedback(true);
    try {
      await api.submitFeedback({
        field_id: fieldId,
        photo_diagnosis_id: risk.photo_diagnosis.id,
        was_accurate: wasAccurate,
        farmer_comment: wasAccurate ? "Farmer confirmed photo diagnosis" : "Farmer flagged photo diagnosis inaccuracy",
      });
      setPhotoFeedbackSaved(true);
    } catch {
      // ignore
    } finally {
      setSubmittingFeedback(false);
    }
  };

  // Split field name into two-line heading format (e.g. Kirkwood — North Block)
  const nameParts = fieldName.includes("—")
    ? fieldName.split("—")
    : fieldName.includes("-")
    ? fieldName.split("-")
    : [fieldName, "Field Area"];

  const primaryHeading = nameParts[0].trim();
  const secondaryHeading = nameParts[1]?.trim() || "Active Block";

  return (
    <section className="panel">
      {/* Field Name Large Two-line Heading */}
      <div className="panel__header">
        <div>
          <h2 style={{ fontSize: "1.45rem", fontWeight: 700, color: "#fff", lineHeight: 1.15 }}>
            {primaryHeading}
          </h2>
          <span style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--accent-primary)", display: "block" }}>
            — {secondaryHeading}
          </span>
          <p className="app__field-subtext">
            Satellite &amp; weather risk analysis updated live
          </p>
        </div>
        <RiskBadge score={risk.score} />
      </div>

      {/* Three-Column Stat Row (Water, Heat, Plants) */}
      <div className="signal-stat-row">
        <div className="signal-stat-col">
          <div className="signal-stat-icon" style={{ color: "var(--accent-low)" }}>
            <WaterIcon size={20} />
          </div>
          <span className="signal-stat-label">Water</span>
          <span className={`signal-stat-value signal-stat-value--${signalStates.water.color}`}>
            {signalStates.water.label}
          </span>
        </div>

        <div className="signal-stat-col">
          <div className="signal-stat-icon" style={{ color: "var(--accent-high)" }}>
            <HeatIcon size={20} />
          </div>
          <span className="signal-stat-label">Heat</span>
          <span className={`signal-stat-value signal-stat-value--${signalStates.heat.color}`}>
            {signalStates.heat.label}
          </span>
        </div>

        <div className="signal-stat-col">
          <div className="signal-stat-icon" style={{ color: "var(--accent-primary)" }}>
            <PlantIcon size={20} />
          </div>
          <span className="signal-stat-label">Plants</span>
          <span className={`signal-stat-value signal-stat-value--${signalStates.plant.color}`}>
            {signalStates.plant.label}
          </span>
        </div>
      </div>

      {/* Interactive Controls & CTA */}
      <div className="condition-panel__ctas">
        {/* Full-width Solid Bright Green Primary CTA Button */}
        <button
          type="button"
          className="primary-action-btn"
          onClick={speakRisk}
        >
          <span>{isSpeaking ? "⏹ Stop advisory" : "What should I do?"}</span>
        </button>

        {/* Wide Rounded Dark Pill "Hear this" Audio Button with Waveform Graphic */}
        <button
          type="button"
          className="waveform-pill-btn"
          onClick={speakRisk}
          disabled={!voiceEnabled}
        >
          <div className="waveform-pill-btn__left">
            <SpeakerIcon size={18} color="var(--accent-low)" />
            <span>{isSpeaking ? "Stop advisory" : "Hear this advisory"}</span>
          </div>
          <div className={`waveform-graphic${isSpeaking ? " is-playing" : ""}`}>
            <span className="waveform-bar waveform-bar--cyan" style={{ height: "12px" }} />
            <span className="waveform-bar waveform-bar--green" style={{ height: "16px" }} />
            <span className="waveform-bar waveform-bar--amber" style={{ height: "8px" }} />
            <span className="waveform-bar waveform-bar--red" style={{ height: "14px" }} />
            <span className="waveform-bar waveform-bar--cyan" style={{ height: "10px" }} />
            <span className="waveform-bar waveform-bar--green" style={{ height: "18px" }} />
            <span className="waveform-bar waveform-bar--amber" style={{ height: "6px" }} />
          </div>
        </button>
      </div>

      {/* Language & Voice Query Sub-actions */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
        <button
          type="button"
          className="field-filter-btn"
          onClick={startVoiceQuery}
          disabled={!window?.SpeechRecognition && !window?.webkitSpeechRecognition}
        >
          {isListening ? "🎙️ Listening…" : "🎙️ Voice Ask"}
        </button>

        {["en", "af", "zu", "nso"].map((lang) => (
          <button
            key={lang}
            type="button"
            className={`field-filter-btn${voiceLanguage === lang ? " is-active" : ""}`}
            onClick={() => setVoiceLanguage(lang)}
          >
            🌐 {LANGUAGE_LABELS[lang]}
          </button>
        ))}

        {isSpeaking && (
          <button
            type="button"
            className="field-filter-btn"
            onClick={togglePauseSpeaking}
          >
            {isPaused ? "▶️ Resume" : "⏸️ Pause"}
          </button>
        )}

        <button
          type="button"
          className="field-filter-btn"
          style={{ marginLeft: "auto" }}
          onClick={onOpenDisclaimer}
        >
          ℹ️ Advisory Disclaimer
        </button>
      </div>

      {/* Collapsible Recommended Checks List */}
      <details className="recommended-checks-details" open>
        <summary className="recommended-checks-summary">
          <span>Recommended Checks &amp; Signals</span>
          <ChevronDownIcon size={16} />
        </summary>
        <div className="recommended-checks-content">
          <ul className="panel__reasons">
            {risk.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>

          <p className="panel__check" style={{ marginTop: "10px" }}>
            <strong>Action:</strong> {risk.recommended_check}
          </p>
        </div>
      </details>

      {/* Farmer Feedback for Water Stress Assessment */}
      <div className="feedback-widget">
        <span className="feedback-label">Was this assessment accurate for your field?</span>
        {!riskFeedbackSaved ? (
          <div className="feedback-buttons">
            <button
              type="button"
              disabled={submittingFeedback}
              onClick={() => handleRiskFeedback(true)}
              className="feedback-btn"
            >
              👍 Yes
            </button>
            <button
              type="button"
              disabled={submittingFeedback}
              onClick={() => handleRiskFeedback(false)}
              className="feedback-btn"
            >
              👎 No
            </button>
          </div>
        ) : (
          <span className="feedback-thankyou">✅ Thank you for validating real farm accuracy!</span>
        )}
      </div>

      {/* Photo Pest / Vision Signal */}
      {risk.photo_diagnosis && (
        <div className="photo-diagnosis-section">
          <div className="photo-diagnosis-title">
            <span style={{ color: "var(--accent-med)" }}>🌿</span>
            <strong style={{ color: "#fff" }}>Photo Vision Signal</strong>
            <span className="photo-diagnosis-tag">Vision AI</span>
          </div>

          <div className="photo-diagnosis-card">
            <div className="photo-diagnosis-meta">
              <span className="photo-diagnosis-category">{risk.photo_diagnosis.category}</span>
              <span className="photo-diagnosis-confidence">
                {Math.round(risk.photo_diagnosis.confidence * 100)}% confidence
              </span>
            </div>
            <p className="photo-diagnosis-description">
              {risk.photo_diagnosis.description}
            </p>

            <div className="feedback-widget feedback-widget--photo">
              <span className="feedback-label">Was this photo diagnosis right?</span>
              {!photoFeedbackSaved ? (
                <div className="feedback-buttons">
                  <button
                    type="button"
                    disabled={submittingFeedback}
                    onClick={() => handlePhotoFeedback(true)}
                    className="feedback-btn"
                  >
                    👍 Yes
                  </button>
                  <button
                    type="button"
                    disabled={submittingFeedback}
                    onClick={() => handlePhotoFeedback(false)}
                    className="feedback-btn"
                  >
                    👎 No
                  </button>
                </div>
              ) : (
                <span className="feedback-thankyou">✅ Photo feedback saved!</span>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
