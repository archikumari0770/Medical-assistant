import { Routes, Route, Link, Navigate } from "react-router-dom";
import { useAuth } from "./auth/AuthContext.jsx";
import RequireRole from "./auth/RequireRole.jsx";
import PatientSearch from "./components/PatientSearch.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Patient from "./pages/Patient.jsx";
import Analysis from "./pages/Analysis.jsx";
import ReceptionDashboard from "./pages/ReceptionDashboard.jsx";
import LabDashboard from "./pages/LabDashboard.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<AuthedShell />} />
    </Routes>
  );
}

function AuthedShell() {
  const { auth } = useAuth();

  if (!auth) return <Navigate to="/login" replace />;

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main">
        <Routes>
          {auth.role === "doctor" && (
            <>
              <Route path="/" element={<Dashboard />} />
              <Route path="/patients/:id" element={<Patient />} />
              <Route path="/patients/:id/analysis" element={<Analysis />} />
            </>
          )}
          {auth.role === "receptionist" && (
            <Route path="/" element={<ReceptionDashboard />} />
          )}
          {auth.role === "lab" && <Route path="/" element={<LabDashboard />} />}
          {auth.role === "admin" && <Route path="/" element={<AdminDashboard />} />}

          {/* Guards so a direct URL hit outside the current role's routes
              above shows a clear message instead of a blank page. */}
          <Route
            path="*"
            element={
              <RequireRole roles={["doctor", "receptionist", "lab", "admin"]}>
                <Navigate to="/" replace />
              </RequireRole>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

function Sidebar() {
  const { auth, logout } = useAuth();

  return (
    <aside className="sidebar">
      <Link to="/" style={{ textDecoration: "none" }}>
        <div className="brand">MedGraph</div>
        <div className="brand-sub">Decision-support prototype</div>
      </Link>

      <div style={{ fontSize: 13, color: "var(--ink-muted)" }}>
        Signed in as <strong style={{ color: "var(--ink)" }}>{auth.fullName}</strong>
        <div className="patient-list-meta" style={{ marginTop: 2 }}>
          {auth.role} · {auth.staffId}
        </div>
      </div>

      {auth.role === "doctor" && <PatientSearch />}

      <button className="btn btn-secondary" onClick={logout} style={{ marginTop: "auto" }}>
        Sign out
      </button>
    </aside>
  );
}