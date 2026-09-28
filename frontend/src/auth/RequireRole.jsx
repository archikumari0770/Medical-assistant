import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

export default function RequireRole({ roles, children }) {
  const { auth } = useAuth();

  if (!auth) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(auth.role)) {
    return (
      <div className="section" style={{ margin: 32 }}>
        <div className="section-body">
          <p className="error-state">
            Your role ({auth.role}) doesn't have access to this page.
          </p>
        </div>
      </div>
    );
  }

  return children;
}
