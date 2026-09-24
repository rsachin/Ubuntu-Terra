import { useEffect, useState } from 'react';
import { api } from './api/client';
import { useFieldDashboard } from './api/useFieldDashboard';
import FieldMap from './components/FieldMap';
import MapErrorBoundary from './components/MapErrorBoundary';
import FieldList from './components/FieldList';
import ConditionPanel from './components/ConditionPanel';
import TrendChart from './components/TrendChart';
import AlertPreview from './components/AlertPreview';

export default function App() {
  const [fields, setFields] = useState(null);
  const [fieldsError, setFieldsError] = useState(null);
  const [selectedFieldId, setSelectedFieldId] = useState(null);
  const [riskByFieldId, setRiskByFieldId] = useState({});

  // Load the field list once, then select the first field by default.
  useEffect(() => {
    api
      .listFields()
      .then((data) => {
        setFields(data);
        if (data.length > 0) setSelectedFieldId(data[0].id);
      })
      .catch((err) => setFieldsError(err.message));
  }, []);

  // Pull risk for every field so the map markers and sidebar can each show a
  // colour without waiting on whichever field happens to be selected.
  useEffect(() => {
    if (!fields?.length) return;
    fields.forEach((field) => {
      api
        .getRisk(field.id)
        .then((risk) => setRiskByFieldId((prev) => ({ ...prev, [field.id]: risk.score })))
        .catch(() => {});
    });
  }, [fields]);

  const dashboard = useFieldDashboard(selectedFieldId);

  return (
    <div className="app">
      <header className="app__header">
        <h1>Ubuntu Terra</h1>
        <p>Early, explained water &amp; crop stress signals for South African farmers</p>
      </header>

      {fieldsError && (
        <div className="app__banner">
          Can't reach the backend at the configured API URL. Confirm it's running and{' '}
          <code>VITE_API_BASE_URL</code> is set correctly.
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
                />
              </MapErrorBoundary>
              <FieldList
                fields={fields}
                selectedFieldId={selectedFieldId}
                riskByFieldId={riskByFieldId}
                onSelect={setSelectedFieldId}
              />
            </>
          )}
        </div>

        <div className="app__right">
          {dashboard.field && <h2 className="app__field-name">{dashboard.field.name}</h2>}
          {dashboard.partial && (
            <p className="app__banner app__banner--minor">
              Some data for this field didn't load — showing what's available.
            </p>
          )}
          <ConditionPanel risk={dashboard.risk} />
          <TrendChart readings={dashboard.readings ?? []} />
          <AlertPreview alerts={dashboard.alerts} />
        </div>
      </main>
    </div>
  );
}
