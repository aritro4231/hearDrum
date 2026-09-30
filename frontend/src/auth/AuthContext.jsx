import { useState } from "react";
import { loginUser, logoutUser, registerUser } from "../api";
import { AuthContext } from "./authStore";

const AUTH_KEY = "hearDrumAuth";

function readStoredAuth() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY) || "null");
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(readStoredAuth);

  const saveAuth = (nextAuth) => {
    localStorage.setItem(AUTH_KEY, JSON.stringify(nextAuth));
    setAuth(nextAuth);
  };

  const register = async (credentials) => {
    const nextAuth = await registerUser(credentials);
    saveAuth(nextAuth);
    return nextAuth;
  };

  const login = async (credentials) => {
    const nextAuth = await loginUser(credentials);
    saveAuth(nextAuth);
    return nextAuth;
  };

  const logout = async () => {
    const token = auth?.token;
    try {
      if (token) await logoutUser(token);
    } finally {
      localStorage.removeItem(AUTH_KEY);
      setAuth(null);
    }
  };

  const value = {
    token: auth?.token || null,
    user: auth?.user || null,
    isAuthenticated: Boolean(auth?.token),
    register,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
