import { useEffect, useState } from "react";
import { api } from "../api.js";
import PatientSearch from "../components/PatientSearch.jsx";
import LabResultForm from "../components/LabResultForm.jsx";

export default function LabDashboard() {
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState(null);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientResults, setPatientResults] = useState([]);

  function loadRecent() {
    api.listRecentLabResults().then(setRecent).catch((err) => setError(err.message));
  }

  useEffect(loadRecent, []);

  async function selectPatient(patient) {
    setSelectedPatient(patient);
    try {
      const results = await api.listLabResultsForPatient(patient.id);
      setPatientResults(results);
    } catch (err) {
      setError(err.message);
    }
  }

  function handleAdded(result) {
    setPatientResults((prev) => [result, ...prev]);
    loadRecent();
  }

  return (
    <>
      <div className="patient-header">
        <div>
          <h1>Lab</h1>
          <div className="patient-header-meta">
            Enter and view results. Clinical notes and diagnoses aren't shown here.
          </div>
        </div>
      </div>

      <div className="section">
        <div className="section-header">
          <span className="section-title">Find a patient</span>
        </div>
        <div className="section-body">
          <PatientSearchClickable onSelect={selectPatient} />
        </div>
      </div>

      {selectedPatient && (
        <div className="section">
          <div className="section-header">
            <span className="section-title">
              {selectedPatient.first_name} {selectedPatient.last_name}
            </span>
            <span className="section-meta">{selectedPatient.external_id}</span>
          </div>
          <div className="section-body">
            <LabResultForm patientId={selectedPatient.id} onAdded={handleAdded} />

            <div className="evidence-group-label" style={{ marginTop: 20 }}>
              Results on file
            </div>
            {patientResults.length === 0 && <p className="empty-state">No results yet.</p>}
            {patientResults.map((r) => (
              <div className="differential-item" key={r.id}>
                <span className="differential-name">
                  {r.test_name}: {r.result_value} {r.unit}
                </span>
                <span className="differential-feature">
                  {r.reference_range && `Reference: ${r.reference_range} · `}
                  {new Date(r.resulted_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="section">
        <div className="section-header">
          <span className="section-title">Recent activity</span>
        </div>
        <div className="section-body">
          {error && <p className="error-state">{error}</p>}
          {recent.length === 0 && !error && <p className="empty-state">No lab results entered yet.</p>}
          {recent.map((r) => (
            <div className="differential-item" key={r.id}>
              <span className="differential-name">
                {r.test_name}: {r.result_value} {r.unit}
              </span>
              <span className="differential-feature">
                {new Date(r.resulted_at).toLocaleString()} · entered by {r.entered_by}
              </span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

/** Local wrapper: PatientSearch is link-based for navigation elsewhere,
 * but the lab flow needs a plain click-to-select instead of a route change. */
function PatientSearchClickable({ onSelect }) {
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState([]);
  const [error, setError] = useState(null);

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
        {patients.map((p) => (
          <li className="patient-list-item" key={p.id}>
            <div style={{ padding: "10px 10px", cursor: "pointer" }} onClick={() => onSelect(p)}>
              <div className="patient-list-name">
                {p.first_name} {p.last_name}
              </div>
              <div className="patient-list-meta">
                {p.external_id} · DOB {p.date_of_birth}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
