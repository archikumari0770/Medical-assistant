import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import PatientProfile from "../components/PatientProfile.jsx";
import PatientEditForm from "../components/PatientEditForm.jsx";
import NoteUpload from "../components/NoteUpload.jsx";

export default function Patient() {
  const { id } = useParams();
  const [patient, setPatient] = useState(null);
  const [encounters, setEncounters] = useState([]);
  const [medications, setMedications] = useState([]);
  const [labResults, setLabResults] = useState([]);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setPatient(null);

    Promise.all([
      api.getPatient(id),
      api.listEncounters(id),
      api.listMedications(id),
      api.listLabResultsForPatient(id),
    ])
      .then(([p, e, m, l]) => {
        if (cancelled) return;
        setPatient(p);
        setEncounters(e);
        setMedications(m);
        setLabResults(l);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <p className="error-state">{error}</p>;
  if (!patient) return <p className="empty-state">Loading patient…</p>;

  return (
    <>
      <div className="patient-header">
        <div>
          <h1>
            {patient.first_name} {patient.last_name}
          </h1>
          <div className="patient-header-meta">
            {patient.external_id} · DOB {patient.date_of_birth} · {patient.sex}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {!editing && (
            <button className="btn btn-secondary" onClick={() => setEditing(true)}>
              Edit
            </button>
          )}
          <Link to={`/patients/${id}/analysis`} className="btn btn-primary">
            New analysis
          </Link>
        </div>
      </div>

      {editing && (
        <div className="section">
          <div className="section-header">
            <span className="section-title">Edit demographics</span>
          </div>
          <div className="section-body">
            <PatientEditForm
              patient={patient}
              onSaved={(updated) => {
                setPatient(updated);
                setEditing(false);
              }}
              onCancel={() => setEditing(false)}
            />
          </div>
        </div>
      )}

      <PatientProfile patient={patient} encounters={encounters} medications={medications} labResults={labResults} />

      <NoteUpload patientId={id} />
    </>
  );
}