import { useEffect, useState } from "react";
import { api } from "../api/client";

// Demo-grade translations — should be reviewed by a native speaker before production use.
export const DISCLAIMER_TEXT = {
  en: "This tool gives an early indication based on satellite and weather data. It is not a diagnosis from a qualified agronomist or agricultural scientist, and it has not yet been validated against real farm outcomes at scale. Always confirm in person before making a costly decision, and consult a local agronomist or extension officer for anything serious.",
  af: "Hierdie hulpmiddel gee 'n vroeë aanduiding gebaseer op satelliet- en weerdata. Dit is nie 'n diagnose van 'n gekwalifiseerde agronoom of landboukundige nie, en is nog nie op skaal teen regte plaasuitslae gevalideer nie. Bevestig altyd in eie persoon voordat u 'n kosbare besluit neem, en raadpleeg 'n plaaslike agronoom of uitbreidingsbeampte vir enigiets ernstigs.",
  zu: "Lethi thuluzi linikeza isikomba sokuqala esisekelwe kwidatha yesathelayithi njezulu. Akusiqinisekiso esivela kwagronomisti okwesifundo zezolimo, futhi asikaze sihloliswe ngamaphuzu aphelele aphumela emasimini angempela. Qinisekisa ubuso nangubuso ngaphambi kokuthatha isinqumo esibiza kakhulu, futhi xhumana nogrnonomisti wendawo noma isikhulu sezolimo uma into ibonakala ingokuthula.",
  nso: "Sedirišwa se se laetsa ka tlase go ya ka datha ya saetelite le ya boso. Ga se diagnoseso yeo e tšwago go agronomisti kgwekgwe goba mošomiši wa temo, gape ga se ya netefatšwa ka dibjalo tša temo tše di kgonthe. Kgonthišetša ka mowa pele o tsenya tšhelete yeo e bohlokwa, gomme o botšiše agronomisti wa legae goba mofsaši wa dikgwebo tša temo ge go le sefe goba sefe se bohlokwa.",
};

export default function DisclaimerModal({ isOpen, onClose, language = "en" }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (isOpen) {
      api
        .getValidationStats()
        .then(setStats)
        .catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="disclaimer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="disclaimer-modal__header">
          <h3>ℹ️ Advisory Disclaimer &amp; Validation Status</h3>
          <button className="disclaimer-modal__close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="disclaimer-modal__body">
          <div className="disclaimer-callout">
            <p><strong>Disclaimer:</strong> {DISCLAIMER_TEXT[language] || DISCLAIMER_TEXT.en}</p>
          </div>

          <div className="validation-stats-box">
            <h4>Real-World Validation Status</h4>
            {stats ? (
              <div className="validation-stats-content">
                <span className="validation-badge">
                  {stats.status === "not_enough_data" ? "⚠️ Early Stage" : "✅ Validated"}
                </span>
                <p className="validation-message">
                  <strong>{stats.message}</strong>
                </p>
                {stats.detail && <p className="validation-detail">{stats.detail}</p>}
              </div>
            ) : (
              <p className="validation-loading">Loading validation statistics…</p>
            )}
          </div>
        </div>

        <div className="disclaimer-modal__footer">
          <button className="disclaimer-btn" onClick={onClose}>
            I Understand
          </button>
        </div>
      </div>
    </div>
  );
}
