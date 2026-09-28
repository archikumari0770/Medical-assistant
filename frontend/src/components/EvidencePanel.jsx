export default function EvidencePanel({ candidate }) {
  if (!candidate) {
    return (
      <div className="section">
        <div className="section-header">
          <span className="section-title">Evidence</span>
        </div>
        <div className="section-body">
          <p className="empty-state">Select a candidate condition to view its supporting evidence.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="section">
      <div className="section-header">
        <span className="section-title">Evidence — {candidate.name}</span>
      </div>
      <div className="section-body">
        <div className="evidence-group-label">Supporting</div>
        {candidate.supporting_evidence.length === 0 && (
          <p className="empty-state">No supporting evidence recorded.</p>
        )}
        {candidate.supporting_evidence.map((e, i) => (
          <div className="evidence-item" key={i}>
            <span className="evidence-source">{e.source.replace(/_/g, " ")}</span>
            {e.description}
          </div>
        ))}

        {candidate.conflicting_evidence.length > 0 && (
          <>
            <div className="evidence-group-label">Conflicting</div>
            {candidate.conflicting_evidence.map((e, i) => (
              <div className="evidence-item conflict" key={i}>
                <span className="evidence-source">{e.source.replace(/_/g, " ")}</span>
                {e.description}
              </div>
            ))}
          </>
        )}

        {candidate.uncertainty_notes && (
          <div className="uncertainty-note">{candidate.uncertainty_notes}</div>
        )}
      </div>
    </div>
  );
}
