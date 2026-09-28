import { createContext, useContext, useState } from "react";
import { api, setAuthToken, setUnauthorizedHandler } from "../api.js";

const AuthContext = createContext(null);

const STORAGE_KEY = "medgraph_auth";

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      // Set this synchronously, during initial render, so it's in place
      // before any child page's own useEffect fires its first request —
      // a useEffect here would run too late and race with that fetch.
      setAuthToken(parsed?.token || null);
      return parsed;
    } catch {
      return null;
    }
  });

  // Registered once; used by api.js to log out automatically on any 401.
  useState(() => {
    setUnauthorizedHandler(() => {
      setAuthToken(null);
      setAuth(null);
      localStorage.removeItem(STORAGE_KEY);
    });
  });

  async function login(email, password) {
    const token = await api.login(email, password);
    // Set the token immediately — before setAuth/navigate — so it's
    // already attached by the time the destination page's effects run.
    setAuthToken(token.access_token);
    const nextAuth = {
      token: token.access_token,
      role: token.role,
      fullName: token.full_name,
      staffId: token.staff_id,
    };
    setAuth(nextAuth);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextAuth));
    return nextAuth;
  }

  function logout() {
    setAuthToken(null);
    setAuth(null);
    localStorage.removeItem(STORAGE_KEY);
  }

  return (
    <AuthContext.Provider value={{ auth, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}