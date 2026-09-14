import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { authStorage } from "@/lib/authStorage";

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(authStorage.get()));

  useEffect(() => {
    const sync = () => setIsAuthenticated(Boolean(authStorage.get()));
    window.addEventListener("reconcile:auth-changed", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("reconcile:auth-changed", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const login = (token: string) => authStorage.set(token);
  const logout = () => authStorage.clear();

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
