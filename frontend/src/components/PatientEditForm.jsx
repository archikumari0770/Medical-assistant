import { useState } from "react";
import { api } from "../api.js";

export default function PatientEditForm({ patient, onSaved, onCancel }) {
  const [form, setForm] = useState({
    first_name: patient.first_name,
    last_name: patient.last_name,
    date_of_birth: patient.date_of_birth,
    sex: patient.sex,
  });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updatePatient(patient.id, form);
      onSaved(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12, maxWidth: 380 }}>
      <div className="field-group">
        <label className="field-label" htmlFor="edit_first_name">
          First name
        </label>
        <input
          id="edit_first_name"
          className="search-input"
          value={form.first_name}
          onChange={(e) => update("first_name", e.target.value)}
          required
        />
      </div>
      <div className="field-group">
        <label className="field-label" htmlFor="edit_last_name">
          Last name
        </label>
        <input
          id="edit_last_name"
          className="search-input"
          value={form.last_name}
          onChange={(e) => update("last_name", e.target.value)}
          required
        />
      </div>
      <div className="field-group">
        <label className="field-label" htmlFor="edit_dob">
          Date of birth
        </label>
        <input
          id="edit_dob"
          className="search-input"
          type="date"
          max={new Date().toISOString().split("T")[0]}
          value={form.date_of_birth}
          onChange={(e) => update("date_of_birth", e.target.value)}
          required
        />
      </div>
      <div className="field-group">
        <label className="field-label" htmlFor="edit_sex">
          Sex
        </label>
        <select id="edit_sex" className="search-input" value={form.sex} onChange={(e) => update("sex", e.target.value)}>
          <option value="unspecified">Prefer not to say</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
          <option value="other">Other</option>
        </select>
      </div>
      {error && <p className="error-state">{error}</p>}
      <div style={{ display: "flex", gap: 10 }}>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}