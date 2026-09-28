import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Dashboard() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    date_of_birth: "",
    sex: "unspecified",
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const patient = await api.createPatient(form);
      navigate(`/patients/${patient.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="patient-header">
        <div>
          <h1>Dashboard</h1>
          <div className="patient-header-meta">Search the panel on the left, or register a new patient below.</div>
        </div>
      </div>

      <div className="section">
        <div className="section-header">
          <span className="section-title">Register a new patient</span>
          <span className="section-meta">ID assigned automatically on creation</span>
        </div>
        <div className="section-body">
          <form onSubmit={handleCreate} style={{ display: "grid", gap: 14, maxWidth: 420 }}>
            <div className="field-group">
              <label className="field-label" htmlFor="first_name">
                First name
              </label>
              <input
                id="first_name"
                className="search-input"
                value={form.first_name}
                onChange={(e) => update("first_name", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="last_name">
                Last name
              </label>
              <input
                id="last_name"
                className="search-input"
                value={form.last_name}
                onChange={(e) => update("last_name", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="date_of_birth">
                Date of birth
              </label>
              <input
                id="date_of_birth"
                className="search-input"
                type="date"
                max={new Date().toISOString().split("T")[0]}
                value={form.date_of_birth}
                onChange={(e) => update("date_of_birth", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="sex">
                Sex
              </label>
              <select
                id="sex"
                className="search-input"
                value={form.sex}
                onChange={(e) => update("sex", e.target.value)}
              >
                <option value="unspecified">Prefer not to say</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </div>
            {error && <p className="error-state">{error}</p>}
            <div>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? "Creating…" : "Create patient"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}