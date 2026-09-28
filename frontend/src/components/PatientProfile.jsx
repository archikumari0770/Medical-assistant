export default function PatientProfile({ patient, encounters, medications, labResults = [] }) {
  return (
    <>
      <div className="section">
        <div className="section-header">
          <span className="section-title">Encounters</span>
          <span className="section-meta">{encounters.length} on file</span>
        </div>
        <div className="section-body">
          {encounters.length === 0 && <p className="empty-state">No encounters recorded.</p>}
          {encounters.map((e) => (
            <div key={e.id} className="differential-item">
              <span className="differential-name">{e.chief_complaint}</span>
              <span className="differential-feature">
                {new Date(e.encounter_date).toLocaleDateString()} — {e.notes || "No additional notes."}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="section">
        <div className="section-header">
          <span className="section-title">Medications</span>
          <span className="section-meta">
            {medications.filter((m) => m.active).length} active
          </span>
        </div>
        <div className="section-body">
          {medications.length === 0 && <p className="empty-state">No medications recorded.</p>}
          {medications.map((m) => (
            <div key={m.id} className="differential-item">
              <span className="differential-name">
                {m.name} {m.dosage && <span style={{ fontFamily: "var(--font-mono)", fontWeight: 400 }}>· {m.dosage}</span>}
              </span>
              <span className="differential-feature">
                {m.active ? "Active" : "Discontinued"} since{" "}
                {new Date(m.started_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="section">
        <div className="section-header">
          <span className="section-title">Lab results</span>
          <span className="section-meta">{labResults.length} on file</span>
        </div>
        <div className="section-body">
          {labResults.length === 0 && <p className="empty-state">No lab results recorded.</p>}
          {labResults.map((r) => (
            <div key={r.id} className="differential-item">
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

      <p className="disclaimer">
        Patient: {patient.first_name} {patient.last_name} ({patient.external_id}), sex: {patient.sex}.
      </p>
    </>
  );
}
