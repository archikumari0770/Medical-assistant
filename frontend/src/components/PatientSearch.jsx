import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api.js";

/**
 * linkTo: (patient) => path, or null to render as a non-clickable lookup
 * list (used by the reception dashboard, which has no chart to navigate to).
 */
export default function PatientSearch({ linkTo = (p) => `/patients/${p.id}` }) {
  // useParams only sees params within the <Routes> tree; this component
  // renders in the sidebar alongside it, so we parse the id from the path.
  const location = useLocation();
  const match = location.pathname.match(/^\/patients\/([^/]+)/);
  const activeId = match ? match[1] : null;
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
        type="text"
        placeholder="Search patients by name"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Search patients"
      />
      <ul className="patient-list" style={{ marginTop: 14 }}>
        {patients.length === 0 && !error && (
          <li className="empty-state">No patients found.</li>
        )}
        {error && <li className="error-state">{error}</li>}
        {patients.map((p) => {
          const inner = (
            <>
              <div className="patient-list-name">
                {p.first_name} {p.last_name}
              </div>
              <div className="patient-list-meta">
                {p.external_id} · DOB {p.date_of_birth}
              </div>
            </>
          );
          return (
            <li className="patient-list-item" key={p.id}>
              {linkTo ? (
                <Link to={linkTo(p)} className={p.id === activeId ? "active" : ""}>
                  {inner}
                </Link>
              ) : (
                <div style={{ padding: "10px 10px" }}>{inner}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
