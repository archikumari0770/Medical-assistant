import { useState } from "react";
import { api } from "../api.js";

export default function NoteUpload({ patientId }) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  async function handleUpload(e) {
    e.preventDefault();
    setSubmitting(true);
    setStatus(null);
    setError(null);
    try {
      await api.uploadDocument(patientId, title, text);
      setStatus(`Indexed "${title}" — it's now searchable and used by future analyses for this patient.`);
      setTitle("");
      setText("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSearch(e) {
    e.preventDefault();
    setSearching(true);
    setSearchError(null);
    try {
      const res = await api.searchDocuments(patientId, query);
      setResults(res.results);
    } catch (err) {
      setSearchError(err.message);
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="section">
      <div className="section-header">
        <span className="section-title">Notes</span>
        <span className="section-meta">indexed for retrieval during analysis</span>
      </div>
      <div className="section-body">
        <form onSubmit={handleUpload} style={{ display: "grid", gap: 10, marginBottom: 20 }}>
          <input
            className="search-input"
            placeholder="Note title (e.g. Follow-up visit, discharge summary)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
          <textarea
            className="free-text-area"
            placeholder="Paste or write the clinical note text here…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            required
          />
          {error && <p className="error-state">{error}</p>}
          {status && <p style={{ color: "var(--accent)", fontSize: 13 }}>{status}</p>}
          <div>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Indexing…" : "Add note"}
            </button>
          </div>
        </form>

        <div className="evidence-group-label">Search this patient's notes</div>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <input
            className="search-input"
            placeholder="e.g. prior chest pain, medication changes"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn btn-secondary" disabled={searching || !query.trim()}>
            {searching ? "Searching…" : "Search"}
          </button>
        </form>
        {searchError && <p className="error-state">{searchError}</p>}
        {results && results.length === 0 && <p className="empty-state">No matching notes found.</p>}
        {results &&
          results.map((r, i) => (
            <div className="evidence-item" key={i}>
              <span className="evidence-source">{r.title || "note"} · score {r.score?.toFixed(3)}</span>
              {r.text}
            </div>
          ))}
      </div>
    </div>
  );
}