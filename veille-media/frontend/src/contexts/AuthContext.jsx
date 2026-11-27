import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { setAccessToken, setAuthLostHandler } from "../services/api";
import { auth } from "../services/endpoints";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Au chargement : on tente de rouvrir la session grâce au cookie de rafraîchissement.
  useEffect(() => {
    setAuthLostHandler(() => setUser(null));
    auth.refresh()
      .then((d) => { setAccessToken(d.access_token); setUser(d.user); })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const d = await auth.login(email, password);
    setAccessToken(d.access_token);
    setUser(d.user);
  }, []);

  const logout = useCallback(async () => {
    try { await auth.logout(); } finally { setAccessToken(null); setUser(null); }
  }, []);

  return <AuthContext.Provider value={{ user, loading, login, logout, isAdmin: user?.role === "admin" }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
