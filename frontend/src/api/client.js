// Calls the Ubuntu Terra backend directly (see ../../../planning.md → "API Design").
// Base URL is configurable via VITE_API_BASE_URL so the same build can point at
// localhost during development and the deployed Render/Railway URL in production.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// --- Owner token ---------------------------------------------------------
// The backend scopes every owner's data to an opaque per-owner token sent as
// X-Owner-Token, so all requests need one.
//
// This is a DEMO-GRADE token store, not production credential storage: the token
// is kept in plain localStorage and never expires. A production version would
// use httpOnly cookies or short-lived access tokens with refresh rotation.
const OWNER_TOKEN_KEY = "ubuntu_terra_owner_token";
const OWNER_ID_KEY = "ubuntu_terra_owner_id";

// Registration is memoised in-flight so the handful of requests the app fires
// on mount don't each race to create (and 409 on) a token for the same owner.
let ownerTokenPromise = null;

function randomOwnerId() {
  return "farmer_" + Math.random().toString(36).substring(2, 9);
}

// Returns the owner token, registering this device's owner_id on first use.
// A 409 means this browser already registered that owner_id but has lost its
// token (e.g. localStorage cleared) — the owner_id is then rotated, since the
// existing token cannot be re-issued.
async function getOwnerToken() {
  const stored = localStorage.getItem(OWNER_TOKEN_KEY);
  if (stored) return stored;

  if (ownerTokenPromise) return ownerTokenPromise;

  ownerTokenPromise = (async () => {
    let ownerId = localStorage.getItem(OWNER_ID_KEY) || randomOwnerId();

    let res = await fetch(`${BASE_URL}/api/owners/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ owner_id: ownerId }),
    });

    if (res.status === 409) {
      ownerId = randomOwnerId();
      res = await fetch(`${BASE_URL}/api/owners/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ owner_id: ownerId }),
      });
    }
    if (!res.ok) {
      throw new Error(`Owner registration failed: ${res.status}`);
    }

    const data = await res.json();
    localStorage.setItem(OWNER_ID_KEY, data.owner_id);
    localStorage.setItem(OWNER_TOKEN_KEY, data.token);
    return data.token;
  })();

  try {
    return await ownerTokenPromise;
  } catch (err) {
    ownerTokenPromise = null; // let the next call retry
    throw err;
  } finally {
    ownerTokenPromise = null;
  }
}

async function request(path, options = {}) {
  const token = await getOwnerToken();
  const headers = { ...(options.headers || {}), "X-Owner-Token": token };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const err = new Error(detail.detail || `Request failed: ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  health: () => request("/api/health"),
  // Exposes the owner_id this device actually registered, so the UI can tell
  // "my fields" from the shared demo fields. Registers on first call.
  getOwnerIdentity: async () => {
    const token = await getOwnerToken();
    return { owner_id: localStorage.getItem(OWNER_ID_KEY), token };
  },
  // Ownership comes from the X-Owner-Token, so the backend takes no owner_id
  // param here — the token's owner (plus the shared demo fields) decides the list.
  listFields: () => request("/api/fields"),
  // owner_id is intentionally not sent: the backend ignores it in favour of the token.
  createField: (data) =>
    request("/api/fields", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getField: (id) => request(`/api/fields/${id}`),
  getReadings: (id) => request(`/api/fields/${id}/readings`),
  getRisk: (id) => request(`/api/fields/${id}/risk`),
  getAlerts: (id) => request(`/api/fields/${id}/alerts`),
  uploadPhoto: async (id, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request(`/api/fields/${id}/photos`, {
      method: "POST",
      body: formData,
    });
  },
  submitFeedback: (data) =>
    request("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getValidationStats: () => request("/api/validation-stats"),
};
