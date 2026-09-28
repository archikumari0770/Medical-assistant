import { useState } from "react";

// Mirrors the symptom set seeded into the knowledge graph by
// scripts/seed_neo4j.py — keep in sync so every chip actually links to
// a graph node.
const COMMON_SYMPTOMS = [
  "fever", "chills", "cough", "productive cough", "sore throat", "runny nose",
  "nasal congestion", "sneezing", "loss of taste or smell", "shortness of breath",
  "wheezing", "chest pain", "pleuritic chest pain", "palpitations", "leg swelling",
  "headache", "one-sided headache", "sensitivity to light", "visual aura",
  "facial swelling", "throat tightness", "hives", "nausea", "vomiting", "diarrhea",
  "abdominal pain", "right upper quadrant pain", "right lower quadrant pain",
  "heartburn", "black stools", "bloating", "fatigue", "muscle aches", "night sweats",
  "weight loss", "joint pain", "back pain", "dizziness", "confusion", "rash",
  "swelling", "urinary frequency", "painful urination", "flank pain",
  "excessive thirst", "fruity breath odor", "sweating", "tremor", "anxiety",
];

export default function SymptomInput({ onSubmit, submitting }) {
  const [selected, setSelected] = useState(new Set());
  const [freeText, setFreeText] = useState("");

  function toggle(symptom) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(symptom)) next.delete(symptom);
      else next.add(symptom);
      return next;
    });
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({ symptoms: Array.from(selected), freeText });
  }

  const canSubmit = (selected.size > 0 || freeText.trim().length > 0) && !submitting;

  return (
    <form onSubmit={handleSubmit}>
      <div className="symptom-chip-grid">
        {COMMON_SYMPTOMS.map((symptom) => (
          <button
            type="button"
            key={symptom}
            className={`symptom-chip${selected.has(symptom) ? " selected" : ""}`}
            onClick={() => toggle(symptom)}
            aria-pressed={selected.has(symptom)}
          >
            {symptom}
          </button>
        ))}
      </div>
      <textarea
        className="free-text-area"
        placeholder="Optional: paste or describe the clinical note in free text — symptoms will also be extracted from here."
        value={freeText}
        onChange={(e) => setFreeText(e.target.value)}
      />
      <div style={{ marginTop: 14 }}>
        <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
          {submitting ? "Running analysis…" : "Run analysis"}
        </button>
      </div>
    </form>
  );
}