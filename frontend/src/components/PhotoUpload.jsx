import { useState } from "react";
import { api } from "../api/client";
import { CameraIcon, WarningIcon, PlayIcon } from "./Icons";

// Real crop leaf photography placeholder for camera viewfinder initialization
const DEFAULT_VIEWFINDER_BG =
  "https://images.unsplash.com/photo-1592417817098-8f3d6ef23a28?auto=format&fit=crop&w=800&q=80";

export default function PhotoUpload({ fieldId, onPhotoUploaded }) {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);

  if (!fieldId) return null;

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Create local object URL for full-bleed viewfinder preview
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    setUploading(true);
    setError(null);

    try {
      const result = await api.uploadPhoto(fieldId, file);
      setStatus({
        kind: "success",
        filename: result.filename,
        status: result.status,
        uploaded_at: result.uploaded_at,
        diagnosis: result.diagnosis,
      });

      if (onPhotoUploaded && result.diagnosis) {
        onPhotoUploaded(result.diagnosis);
      }
    } catch (err) {
      setError(err.message || "Photo upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const speakDiagnosis = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const diag = status?.diagnosis;
    if (!diag) return;
    const text = `Photo diagnosis: ${diag.category}. ${diag.description}`;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
  };

  const bgImage = previewUrl || DEFAULT_VIEWFINDER_BG;
  const isHighSeverity = status?.diagnosis?.category?.toLowerCase().includes("high") || false;

  return (
    <section className="panel" id="photo-upload-section">
      <div className="panel__header">
        <div>
          <h2>Camera Diagnosis &amp; Vision AI</h2>
          <p className="panel__hint">
            Native crop leaf viewfinder — instant visual pest &amp; disease analysis
          </p>
        </div>
        <CameraIcon size={22} color="var(--accent-primary)" />
      </div>

      {/* Native Phone Frame Chrome Wrapper */}
      <div className="phone-chrome">
        {/* Top Notch / Dynamic Island */}
        <div className="phone-chrome__notch" />

        {/* Viewfinder with Real Captured/Preview Photo Full-Bleed */}
        <div
          className="phone-viewfinder"
          style={{ backgroundImage: `url(${bgImage})` }}
        >
          {/* Corner L-Brackets (Camera focus indicators) */}
          <div className="corner-bracket corner-bracket--tl" />
          <div className="corner-bracket corner-bracket--tr" />
          <div className="corner-bracket corner-bracket--bl" />
          <div className="corner-bracket corner-bracket--br" />

          {/* Uploading indicator */}
          {uploading && (
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                background: "rgba(0,0,0,0.8)",
                padding: "8px 16px",
                borderRadius: "20px",
                color: "var(--accent-primary)",
                fontWeight: "600",
                fontSize: "0.85rem",
                zIndex: 10,
              }}
            >
              Analyzing leaf pixels…
            </div>
          )}

          <div style={{ flex: 1 }} />

          {/* Results Overlay Banner on lower portion of viewfinder image */}
          {status?.diagnosis && (
            <div className="phone-viewfinder__overlay">
              <div
                className={`diagnosis-banner${isHighSeverity ? " diagnosis-banner--high" : ""}`}
              >
                <WarningIcon size={18} />
                <span>
                  {status.diagnosis.category} (
                  {Math.round(status.diagnosis.confidence * 100)}% Match)
                </span>
              </div>
              <div className="diagnosis-result-panel">
                <p className="diagnosis-result-text">
                  {status.diagnosis.description}
                </p>
                <button
                  type="button"
                  onClick={speakDiagnosis}
                  style={{
                    background: "var(--accent-primary)",
                    border: "none",
                    borderRadius: "50%",
                    width: "32px",
                    height: "32px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    boxShadow: "0 0 10px rgba(46,213,115,0.5)",
                  }}
                  title="Hear spoken diagnosis"
                  aria-label="Hear spoken diagnosis"
                >
                  <PlayIcon size={14} color="#0a140c" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Shutter Button & Native Device Home Bar */}
        <div className="phone-shutter-area">
          <label className="phone-shutter-btn" title="Take or upload crop photo">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              disabled={uploading}
              style={{ display: "none" }}
            />
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "50%",
                border: "2px solid #000",
                background: "#fff",
              }}
            />
          </label>
          <span style={{ fontSize: "0.75rem", color: "var(--ink-soft)" }}>
            Tap shutter to analyze leaf
          </span>
          <div className="phone-home-indicator" />
        </div>
      </div>

      {error && (
        <p className="app__banner" style={{ marginTop: "14px" }}>
          {error}
        </p>
      )}
    </section>
  );
}
