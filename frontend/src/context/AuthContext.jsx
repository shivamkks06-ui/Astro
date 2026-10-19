import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";
import { tokens } from "../lib/native";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const refreshMe = useCallback(async () => {
    try {
      await tokens.load();
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch (e) {
      setUser(false);
    }
  }, []);
  useEffect(() => {
    refreshMe();
    window.addEventListener("app:resume", refreshMe);
    return () => window.removeEventListener("app:resume", refreshMe);
  }, [refreshMe]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    await tokens.save(data);
    setUser(data.user);
    return data.user;
  };
  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    await tokens.save(data);
    setUser(data.user);
    return data.user;
  };
  const logout = async () => {
    try { await api.post("/auth/logout"); } finally { await tokens.clear(); setUser(false); }
  };
  return <AuthCtx.Provider value={{ user, login, register, logout, refreshMe }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);

export const homeFor = (u) => (u?.role === "admin" ? "/admin" : u?.role === "astrologer" ? "/studio" : "/account");
