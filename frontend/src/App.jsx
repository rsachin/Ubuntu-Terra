import { useEffect, useState } from "react";
import { api } from "./api/client";
import { useFieldDashboard } from "./api/useFieldDashboard";
import FieldMap from "./components/FieldMap";
import MapErrorBoundary from "./components/MapErrorBoundary";
import FieldList from "./components/FieldList";
import ConditionPanel from "./components/ConditionPanel";
import TrendChart from "./components/TrendChart";
import AlertPreview from "./components/AlertPreview";
import PhotoUpload from "./components/PhotoUpload";
import DisclaimerModal from "./components/DisclaimerModal";

export default function App() {
  const [fields, setFields] = useState(null);
  const [fieldsError, setFieldsError] = useState(null);
  const [selectedFieldId, setSelectedFieldId] = useState(null);
  const [riskByFieldId, setRiskByFieldId] = useState({});
  const [filterMyFields, setFilterMyFields] = useState(false);
  const [isDisclaimerOpen, setIsDisclaimerOpen] = useState(false);

  // Owner identity is owned by the API client (see api/client.js): the backend
  // scopes data by the X-Owner-Token, so the UI must compare against the
  // owner_id that was actually registered rather than a locally invented one.
  const [ownerId, setOwnerId] = useState(
    () => localStorage.getItem("ubuntu_terra_owner_id") || "",
  );

  // Load the field list once, then select the first field by default.
  useEffect(() => {
    api
      .getOwnerIdentity()
      .then(({ owner_id }) => setOwnerId(owner_id))
      .catch(() => {});

    api
      .listFields()
      .then((data) => {
        setFields(data);
        if (data.length > 0) setSelectedFieldId(data[0].id);
      })
      .catch((err) => setFieldsError(err.message));
  }, []);

  // Pull risk for every field so markers and sidebar show risk colors
  useEffect(() => {
    if (!fields?.length) return;
    fields.forEach((field) => {
      api
        .getRisk(field.id)
        .then((risk) =>
          setRiskByFieldId((prev) => ({ ...prev, [field.id]: risk.score })),
        )
        .catch(() => {});
    });
  }, [fields]);

  const dashboard = useFieldDashboard(selectedFieldId);

  // Onboard new field
  const handleAddField = async (fieldPayload) => {
    // No owner_id is sent: the backend assigns ownership from the X-Owner-Token
    // and ignores any owner_id in the body.
    const created = await api.createField(fieldPayload);

    setFields((prev) => (prev ? [...prev, created] : [created]));
    setSelectedFieldId(created.id);

    api
      .getRisk(created.id)
      .then((risk) =>
        setRiskByFieldId((prev) => ({ ...prev, [created.id]: risk.score })),
      )
      .catch(() => {});

    return created;
  };

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-top">
          <h1>Ubuntu Terra</h1>
          <button
            type="button"
            className="disclaimer-info-btn"
            onClick={() => setIsDisclaimerOpen(true)}
            title="View advisory disclaimer & validation stats"
          >
            ℹ️ Advisory Disclaimer &amp; Stats
          </button>
        </div>
        <p>
          Early, explained water &amp; crop stress signals for South African
          farmers
        </p>
      </header>

      {fieldsError && (
        <div className="app__banner">
          Can't reach the backend at the configured API URL. Confirm it's
          running and <code>VITE_API_BASE_URL</code> is set correctly.
        </div>
      )}

      <main className="app__body">
        <div className="app__left">
          {fields && (
            <>
              <MapErrorBoundary>
                <FieldMap
                  fields={fields}
                  selectedFieldId={selectedFieldId}
                  riskByFieldId={riskByFieldId}
                  onSelect={setSelectedFieldId}
                  onAddField={handleAddField}
                />
              </MapErrorBoundary>
              <FieldList
                fields={fields}
                selectedFieldId={selectedFieldId}
                riskByFieldId={riskByFieldId}
                onSelect={setSelectedFieldId}
                ownerId={ownerId}
                filterMyFields={filterMyFields}
                onToggleFilter={setFilterMyFields}
              />
            </>
          )}
        </div>

        <div className="app__right">
          {dashboard.loading && selectedFieldId && (
            <p className="app__banner app__banner--minor">
              Loading field data…
            </p>
          )}
          {dashboard.field && (
            <h2 className="app__field-name">{dashboard.field.name}</h2>
          )}
          {dashboard.partial && (
            <p className="app__banner app__banner--minor">
              Some data for this field didn't load — showing what's available.
            </p>
          )}
          <ConditionPanel
            risk={dashboard.risk}
            readings={dashboard.readings ?? []}
            fieldId={selectedFieldId}
            onOpenDisclaimer={() => setIsDisclaimerOpen(true)}
          />
          <TrendChart readings={dashboard.readings ?? []} />
          <AlertPreview alerts={dashboard.alerts} />
          <PhotoUpload fieldId={selectedFieldId} />
        </div>
      </main>

      <DisclaimerModal
        isOpen={isDisclaimerOpen}
        onClose={() => setIsDisclaimerOpen(false)}
      />
    </div>
  );
}
