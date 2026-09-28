import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import SymptomInput from "../components/SymptomInput.jsx";
import DiagnosisPanel from "../components/DiagnosisPanel.jsx";
import EvidencePanel from "../components/EvidencePanel.jsx";
import WhyPanel from "../components/WhyPanel.jsx";

export default function Analysis() {
  const { id } = useParams();
  const [patient, setPatient] = useState(null);
  const [result, setResult] = useState(null);
  const [selectedName, setSelectedName] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getPatient(id).then(setPatient).catch((err) => setError(err.message));
  }, [id]);

  async function handleRun({ symptoms, freeText }) {
    setSubmitting(true);
    setError(null);
    setResult(null);
    setSelectedName(null);
    try {
      const res = await api.runAnalysis(id, { symptoms, freeText });
      setResult(res);
      if (res.candidates.length > 0) setSelectedName(res.candidates[0].name);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const selectedCandidate = result?.candidates.find((c) => c.name === selectedName) || null;

  return (
    <>
      <div className="patient-header">
        <div>
          <h1>Analysis</h1>
          <div className="patient-header-meta">
            {patient ? (
              <Link to={`/patients/${id}`}>
                {patient.first_name} {patient.last_name} · {patient.external_id}
              </Link>
            ) : (
              "Loading patient…"
            )}
          </div>
        </div>
      </div>

      <div className="section">
        <div className="section-header">
          <span className="section-title">Symptoms</span>
        </div>
        <div className="section-body">
          <SymptomInput onSubmit={handleRun} submitting={submitting} />
        </div>
      </div>

      {error && (
        <div className="section">
          <div className="section-body">
            <p className="error-state">{error}</p>
          </div>
        </div>
      )}

      {result && (
        <>
          <DiagnosisPanel result={result} selectedName={selectedName} onSelect={setSelectedName} />
          <EvidencePanel candidate={selectedCandidate} />
          <WhyPanel candidate={selectedCandidate} allCandidates={result.candidates} />

          <div className="section">
            <div className="section-header">
              <span className="section-title">Summary</span>
            </div>
            <div className="section-body">
              <p className="narrative">{result.narrative_summary}</p>
              <p className="disclaimer">{result.disclaimer}</p>
            </div>
          </div>
        </>
      )}
    </>
  );
}
