import { createContext, useContext, useEffect, useMemo, useState } from "react";
import api, { TOKEN_KEY } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get("/api/auth/me")
      .then((response) => setUser(response.data))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo(() => {
    async function login(email, password) {
      const response = await api.post("/api/auth/login", { email, password });
      localStorage.setItem(TOKEN_KEY, response.data.access_token);
      setUser(response.data.user);
      return response.data.user;
    }

    async function register(payload) {
      const response = await api.post("/api/auth/register", payload);
      localStorage.setItem(TOKEN_KEY, response.data.access_token);
      setUser(response.data.user);
      return response.data.user;
    }

    function logout() {
      localStorage.removeItem(TOKEN_KEY);
      // Cart is per browser session of a signed-in student. Clear it so the next person
      // on a shared laptop does not inherit the previous order.
      window.dispatchEvent(new Event("cb:cart-clear"));
      setUser(null);
    }

    return {
      user,
      loading,
      login,
      register,
      logout,
      token: localStorage.getItem(TOKEN_KEY),
    };
  }, [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
