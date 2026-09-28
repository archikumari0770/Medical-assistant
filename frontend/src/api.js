const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

let authToken = null;
let onUnauthorized = null;

export function setAuthToken(token) {
  authToken = token;
}

/** Registered by AuthProvider so a 401 anywhere logs the user out. */
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401 && onUnauthorized) {
    onUnauthorized();
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* response wasn't JSON — keep statusText */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // --- Auth ---
  login: async (email, password) => {
    // Login uses OAuth2PasswordRequestForm on the backend, which expects
    // form-encoded 'username'/'password', not JSON.
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) {
      let detail = "Login failed";
      try {
        detail = (await res.json()).detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    return res.json();
  },
  me: () => request("/auth/me"),

  // --- Patients ---
  listPatients: (q = "", includeArchived = false) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (includeArchived) params.set("include_archived", "true");
    const qs = params.toString();
    return request(`/patients${qs ? `?${qs}` : ""}`);
  },
  getPatient: (id) => request(`/patients/${id}`),
  createPatient: (payload) =>
    request("/patients", { method: "POST", body: JSON.stringify(payload) }),
  updatePatient: (id, payload) =>
    request(`/patients/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  archivePatient: (id) => request(`/patients/${id}/archive`, { method: "PATCH" }),
  restorePatient: (id) => request(`/patients/${id}/restore`, { method: "PATCH" }),
  deletePatient: (id) => request(`/patients/${id}`, { method: "DELETE" }),

  listEncounters: (patientId) => request(`/patients/${patientId}/encounters`),
  addEncounter: (patientId, payload) =>
    request(`/patients/${patientId}/encounters`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listMedications: (patientId) => request(`/patients/${patientId}/medications`),
  addMedication: (patientId, payload) =>
    request(`/patients/${patientId}/medications`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // --- Documents (patient-scoped RAG) ---
  uploadDocument: (patientId, title, text) =>
    request("/documents", {
      method: "POST",
      body: JSON.stringify({ patient_id: patientId, title, text }),
    }),
  searchDocuments: (patientId, query, topK = 5) =>
    request("/documents/search", {
      method: "POST",
      body: JSON.stringify({ patient_id: patientId, query, top_k: topK }),
    }),

  // --- Analysis ---
  runAnalysis: (patientId, { symptoms = [], freeText = "" }) =>
    request("/analysis", {
      method: "POST",
      body: JSON.stringify({ patient_id: patientId, symptoms, free_text: freeText }),
    }),

  // --- Labs ---
  addLabResult: (payload) =>
    request("/labs", { method: "POST", body: JSON.stringify(payload) }),
  listLabResultsForPatient: (patientId) => request(`/labs/patient/${patientId}`),
  listRecentLabResults: (limit = 25) => request(`/labs/recent?limit=${limit}`),

  // --- Admin ---
  listUsers: () => request("/admin/users"),
  createUser: (payload) =>
    request("/admin/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (userId, payload) =>
    request(`/admin/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) }),
};