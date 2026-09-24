import { useEffect, useState } from 'react';
import { api } from './client';

// Loads everything the dashboard needs for one selected field. Each call is
// independent so a failure in one (e.g. risk engine) doesn't blank out data
// that did load (e.g. readings) — mirrors the backend's own "never leave the
// panel fully blank" resilience described in planning.md's User Flows.
export function useFieldDashboard(fieldId) {
  const [state, setState] = useState({
    loading: true,
    error: null,
    field: null,
    readings: null,
    risk: null,
    alerts: null,
  });

  useEffect(() => {
    if (fieldId == null) return;
    let cancelled = false;

    setState((s) => ({ ...s, loading: true, error: null }));

    Promise.allSettled([
      api.getField(fieldId),
      api.getReadings(fieldId),
      api.getRisk(fieldId),
      api.getAlerts(fieldId),
    ]).then(([field, readings, risk, alerts]) => {
      if (cancelled) return;

      const anyFailed = [field, readings, risk, alerts].some((r) => r.status === 'rejected');
      const allFailed = [field, readings, risk, alerts].every((r) => r.status === 'rejected');

      setState({
        loading: false,
        error: allFailed ? (field.reason?.message ?? 'Could not reach the backend.') : null,
        field: field.status === 'fulfilled' ? field.value : null,
        readings: readings.status === 'fulfilled' ? readings.value : null,
        risk: risk.status === 'fulfilled' ? risk.value : null,
        alerts: alerts.status === 'fulfilled' ? alerts.value : null,
        partial: anyFailed && !allFailed,
      });
    });

    return () => {
      cancelled = true;
    };
  }, [fieldId]);

  return state;
}
