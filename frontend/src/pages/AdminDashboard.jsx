import { useEffect, useState } from "react";
import { api } from "../api.js";

const ROLES = ["admin", "doctor", "receptionist", "lab"];

export default function AdminDashboard() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "doctor" });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);

  function loadUsers() {
    api.listUsers().then(setUsers).catch((err) => setError(err.message));
  }

  useEffect(loadUsers, []);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      await api.createUser(form);
      setForm({ email: "", password: "", full_name: "", role: "doctor" });
      loadUsers();
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(user) {
    try {
      await api.updateUser(user.id, { is_active: !user.is_active });
      loadUsers();
    } catch (err) {
      setError(err.message);
    }
  }

  async function changeRole(user, role) {
    try {
      await api.updateUser(user.id, { role });
      loadUsers();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <div className="patient-header">
        <div>
          <h1>Admin</h1>
          <div className="patient-header-meta">Manage staff accounts and access.</div>
        </div>
      </div>

      <div className="section">
        <div className="section-header">
          <span className="section-title">Create a staff account</span>
        </div>
        <div className="section-body">
          <form onSubmit={handleCreate} style={{ display: "grid", gap: 14, maxWidth: 420 }}>
            <div className="field-group">
              <label className="field-label" htmlFor="new_email">
                Email
              </label>
              <input
                id="new_email"
                className="search-input"
                type="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="new_full_name">
                Full name
              </label>
              <input
                id="new_full_name"
                className="search-input"
                value={form.full_name}
                onChange={(e) => update("full_name", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="new_password">
                Temporary password
              </label>
              <input
                id="new_password"
                className="search-input"
                type="text"
                minLength={8}
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="new_role">
                Role
              </label>
              <select
                id="new_role"
                className="search-input"
                value={form.role}
                onChange={(e) => update("role", e.target.value)}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
            {createError && <p className="error-state">{createError}</p>}
            <div>
              <button type="submit" className="btn btn-primary" disabled={creating}>
                {creating ? "Creating…" : "Create account"}
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="section">
        <div className="section-header">
          <span className="section-title">All accounts</span>
          <span className="section-meta">{users.length} total</span>
        </div>
        <div className="section-body">
          {error && <p className="error-state">{error}</p>}
          {users.map((u) => (
            <div key={u.id} className="candidate-row" style={{ cursor: "default" }}>
              <div className="candidate-top-line">
                <span className="candidate-name" style={{ opacity: u.is_active ? 1 : 0.5 }}>
                  {u.full_name}{" "}
                  <span style={{ color: "var(--ink-muted)", fontWeight: 400 }}>
                    · {u.staff_id} · {u.email}
                  </span>
                </span>
              </div>
              <div style={{ marginLeft: 0, marginTop: 8, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <select
                  className="search-input"
                  style={{ width: "auto", padding: "5px 28px 5px 10px", fontSize: 13 }}
                  value={u.role}
                  onChange={(e) => changeRole(u, e.target.value)}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <button className="btn btn-secondary" style={{ padding: "5px 12px", fontSize: 13 }} onClick={() => toggleActive(u)}>
                  {u.is_active ? "Deactivate" : "Reactivate"}
                </button>
                {!u.is_active && <span style={{ fontSize: 12, color: "var(--warning)" }}>Deactivated</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      <PatientRecordsPanel />
    </>
  );
}

function PatientRecordsPanel() {
  const [query, setQuery] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [patients, setPatients] = useState([]);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);

  function load() {
    api
      .listPatients(query, includeArchived)
      .then(setPatients)
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, includeArchived]);

  async function handleArchive(patient) {
    setActionError(null);
    try {
      await api.archivePatient(patient.id);
      load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleRestore(patient) {
    setActionError(null);
    try {
      await api.restorePatient(patient.id);
      load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleDelete(patient) {
    setActionError(null);
    const confirmed = window.confirm(
      `Permanently delete ${patient.first_name} ${patient.last_name} (${patient.external_id})? ` +
        `This only succeeds if the record has no clinical history, and can't be undone.`
    );
    if (!confirmed) return;
    try {
      await api.deletePatient(patient.id);
      load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <div className="section">
      <div className="section-header">
        <span className="section-title">Patient records</span>
      </div>
      <div className="section-body">
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
          <input
            className="search-input"
            style={{ maxWidth: 320 }}
            placeholder="Search patients by name"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <label style={{ fontSize: 13, color: "var(--ink-muted)", display: "flex", gap: 6, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
            />
            Show archived
          </label>
        </div>

        {error && <p className="error-state">{error}</p>}
        {actionError && <p className="error-state">{actionError}</p>}
        {patients.length === 0 && !error && <p className="empty-state">No patients found.</p>}

        {patients.map((p) => (
          <div key={p.id} className="candidate-row" style={{ cursor: "default" }}>
            <div className="candidate-top-line">
              <span className="candidate-name" style={{ opacity: p.is_archived ? 0.5 : 1 }}>
                {p.first_name} {p.last_name}{" "}
                <span style={{ color: "var(--ink-muted)", fontWeight: 400 }}>
                  · {p.external_id} · DOB {p.date_of_birth}
                </span>
                {p.is_archived && (
                  <span style={{ marginLeft: 8, fontSize: 11, color: "var(--warning)", fontFamily: "var(--font-mono)" }}>
                    ARCHIVED
                  </span>
                )}
              </span>
            </div>
            <div style={{ marginTop: 8, display: "flex", gap: 10, flexWrap: "wrap" }}>
              {p.is_archived ? (
                <button className="btn btn-secondary" style={{ padding: "5px 12px", fontSize: 13 }} onClick={() => handleRestore(p)}>
                  Restore
                </button>
              ) : (
                <button className="btn btn-secondary" style={{ padding: "5px 12px", fontSize: 13 }} onClick={() => handleArchive(p)}>
                  Archive
                </button>
              )}
              <button
                className="btn btn-secondary"
                style={{ padding: "5px 12px", fontSize: 13, borderColor: "var(--critical)", color: "var(--critical)" }}
                onClick={() => handleDelete(p)}
              >
                Delete…
              </button>
            </div>
          </div>
        ))}

        <p className="disclaimer">
          Archiving hides a patient from active use without deleting anything, and can be undone.
          Permanent deletion only succeeds for records with no encounters, medications, lab
          results, or indexed notes — everything else should be archived instead.
        </p>
      </div>
    </div>
  );
}