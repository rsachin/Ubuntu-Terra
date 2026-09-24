// Calls the Ubuntu Terra backend directly (see ../../../planning.md → "API Design").
// Base URL is configurable via VITE_API_BASE_URL so the same build can point at
// localhost during development and the deployed Render/Railway URL in production.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const err = new Error(detail.detail || `Request failed: ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  health: () => request('/api/health'),
  listFields: () => request('/api/fields'),
  getField: (id) => request(`/api/fields/${id}`),
  getReadings: (id) => request(`/api/fields/${id}/readings`),
  getRisk: (id) => request(`/api/fields/${id}/risk`),
  getAlerts: (id) => request(`/api/fields/${id}/alerts`),
};
