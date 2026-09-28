import { useState } from "react";
import { api } from "../api.js";

export default function LabResultForm({ patientId, onAdded }) {
  const [form, setForm] = useState({ test_name: "", result_value: "", unit: "", reference_range: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.addLabResult({ patient_id: patientId, ...form });
      setForm({ test_name: "", result_value: "", unit: "", reference_range: "" });
      onAdded?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: 10, gridTemplateColumns: "2fr 1fr 1fr 1fr auto" }}>
      <input
        className="search-input"
        placeholder="Test name (e.g. CBC — WBC count)"
        value={form.test_name}
        onChange={(e) => update("test_name", e.target.value)}
        required
      />
      <input
        className="search-input"
        placeholder="Result"
        value={form.result_value}
        onChange={(e) => update("result_value", e.target.value)}
        required
      />
      <input
        className="search-input"
        placeholder="Unit"
        value={form.unit}
        onChange={(e) => update("unit", e.target.value)}
      />
      <input
        className="search-input"
        placeholder="Reference range"
        value={form.reference_range}
        onChange={(e) => update("reference_range", e.target.value)}
      />
      <button type="submit" className="btn btn-primary" disabled={submitting}>
        {submitting ? "Saving…" : "Add result"}
      </button>
      {error && (
        <p className="error-state" style={{ gridColumn: "1 / -1" }}>
          {error}
        </p>
      )}
    </form>
  );
}
