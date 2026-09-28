function evidenceCounts(candidate) {
  const graph = candidate.supporting_evidence.filter((e) => e.source === "knowledge_graph").length;
  const literature = candidate.supporting_evidence.filter((e) => e.source === "medical_literature").length;
  const conflicts = candidate.conflicting_evidence.length;
  return { graph, literature, conflicts };
}

export default function WhyPanel({ candidate, allCandidates }) {
  if (!candidate) {
    return (
      <div className="section">
        <div className="section-header">
          <span className="section-title">Why this ranking</span>
        </div>
        <div className="section-body">
          <p className="empty-state">Select a candidate to see how it compares to its closest competitor.</p>
        </div>
      </div>
    );
  }

  const index = allCandidates.findIndex((c) => c.name === candidate.name);
  const competitor = index === 0 ? allCandidates[1] : allCandidates[index - 1];
  const counts = evidenceCounts(candidate);

  return (
    <div className="section">
      <div className="section-header">
        <span className="section-title">Why this ranking</span>
      </div>
      <div className="section-body">
        <div className="differential-item">
          <span className="differential-name">
            {counts.graph} symptom match{counts.graph === 1 ? "" : "es"} in the knowledge graph
          </span>
          <span className="differential-feature">
            {counts.literature} supporting literature excerpt{counts.literature === 1 ? "" : "s"}
            {counts.conflicts > 0 && `, ${counts.conflicts} conflicting note${counts.conflicts === 1 ? "" : "s"} from patient history`}
          </span>
        </div>

        {competitor ? (
          <div className="differential-item">
            <span className="differential-name">
              Compared to {competitor.name} (score {competitor.score.toFixed(2)} vs {candidate.score.toFixed(2)})
            </span>
            <span className="differential-feature">
              {candidate.score === competitor.score
                ? "Evidence strength is currently tied — additional history or targeted testing would help separate these."
                : candidate.score > competitor.score
                ? "Ranked higher on cumulative graph and literature evidence weight; review both before narrowing."
                : "Ranked lower — reconsider if new findings shift the evidence balance."}
            </span>
          </div>
        ) : (
          <p className="empty-state">Only one candidate was generated — no direct competitor to compare against.</p>
        )}
      </div>
    </div>
  );
}
