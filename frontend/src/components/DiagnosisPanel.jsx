export default function DiagnosisPanel({ result, selectedName, onSelect }) {
  const { candidates, safety_flags: safetyFlags } = result;

  return (
    <>
      {safetyFlags.length > 0 && (
        <div className="section">
          <div className="section-header">
            <span className="section-title">Safety flags</span>
          </div>
          <div className="section-body">
            {safetyFlags.map((flag, i) => (
              <div key={i} className={`safety-flag ${flag.severity}`}>
                <span className="safety-flag-label">{flag.severity}</span>
                <span>{flag.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="section">
        <div className="section-header">
          <span className="section-title">Candidate conditions</span>
          <span className="section-meta">ranked by relative evidence, not probability</span>
        </div>
        <div className="section-body">
          {candidates.length === 0 && (
            <p className="empty-state">No candidates generated for the given input.</p>
          )}
          <div className="candidate-list">
            {candidates.map((c, i) => (
              <div
                key={c.name}
                className={`candidate-row${c.name === selectedName ? " selected" : ""}`}
                onClick={() => onSelect(c.name)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && onSelect(c.name)}
              >
                <div className="candidate-top-line">
                  <span className="candidate-rank">{i + 1}</span>
                  <span className="candidate-name">{c.name}</span>
                  <span className="candidate-score-value">{c.score.toFixed(2)}</span>
                </div>
                <div className="score-bar-track">
                  <div className="score-bar-fill" style={{ width: `${c.score * 100}%` }} />
                </div>
                {c.uncertainty_notes && (
                  <div className="candidate-flag-inline">{c.uncertainty_notes}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
