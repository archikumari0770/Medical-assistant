import { useEffect, useState } from "react";
import { api } from "../api.js";
import PatientEditForm from "../components/PatientEditForm.jsx";

export default function ReceptionDashboard() {
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    date_of_birth: "",
    sex: "unspecified",
  });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const patient = await api.createPatient(form);
      setSuccess(
        `Registered ${patient.first_name} ${patient.last_name} — assigned ID ${patient.external_id}.`
      );
      setForm({ first_name: "", last_name: "", date_of_birth: "", sex: "unspecified" });
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
          <h1>Front desk</h1>
          <div className="patient-header-meta">
            Patient registration and lookup. Clinical notes and diagnoses aren't shown here.
          </div>
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
              <label className="field-label" htmlFor="r_first_name">
                First name
              </label>
              <input
                id="r_first_name"
                className="search-input"
                value={form.first_name}
                onChange={(e) => update("first_name", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="r_last_name">
                Last name
              </label>
              <input
                id="r_last_name"
                className="search-input"
                value={form.last_name}
                onChange={(e) => update("last_name", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="r_date_of_birth">
                Date of birth
              </label>
              <input
                id="r_date_of_birth"
                className="search-input"
                type="date"
                max={new Date().toISOString().split("T")[0]}
                value={form.date_of_birth}
                onChange={(e) => update("date_of_birth", e.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor="r_sex">
                Sex
              </label>
              <select
                id="r_sex"
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
            {success && <p style={{ color: "var(--accent)", fontSize: 13 }}>{success}</p>}
            <div>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? "Registering…" : "Register patient"}
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="section">
        <div className="section-header">
          <span className="section-title">Look up or edit a patient</span>
        </div>
        <div className="section-body">
          <PatientLookupAndEdit />
        </div>
      </div>
    </>
  );
}

function PatientLookupAndEdit() {
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState([]);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const results = await api.listPatients(query);
        if (!cancelled) setPatients(results);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  return (
    <div>
      <input
        className="search-input"
        placeholder="Search patients by name"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <ul className="patient-list" style={{ marginTop: 14 }}>
        {error && <li className="error-state">{error}</li>}
        {patients.length === 0 && !error && <li className="empty-state">No patients found.</li>}
        {patients.map((p) => (
          <li className="patient-list-item" key={p.id}>
            <div
              style={{ padding: "10px 10px", cursor: "pointer" }}
              onClick={() => setSelected(selected?.id === p.id ? null : p)}
            >
              <div className="patient-list-name">
                {p.first_name} {p.last_name}
              </div>
              <div className="patient-list-meta">
                {p.external_id} · DOB {p.date_of_birth}
              </div>
            </div>
            {selected?.id === p.id && (
              <div style={{ padding: "0 10px 14px 10px" }}>
                <PatientEditForm
                  patient={selected}
                  onSaved={(updated) => {
                    setSelected(null);
                    setPatients((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
                  }}
                  onCancel={() => setSelected(null)}
                />
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}