import React, { createContext, useContext, useEffect, useState } from "react";
import * as api from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      setLoading(false);
      return;
    }

    api
      .getMe()
      .then((res) => {
        setUser(res.data);
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("username");
        localStorage.removeItem("full_name");
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const doLogin = async (username, password) => {
    // Send credentials to the FastAPI backend.
    const res = await api.login(username, password);

    // Backend returns access_token, username and full_name.
    const {
      access_token,
      username: loggedUsername,
      full_name,
    } = res.data;

    // Make sure the backend actually returned a token.
    if (!access_token) {
      throw new Error("Login succeeded but no access token was returned.");
    }

    // Store authentication information.
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("username", loggedUsername || username);
    localStorage.setItem("full_name", full_name || "");

    // Authentication is successful at this point.
    // Do not make /me a requirement for login success.
    setUser({
      username: loggedUsername || username,
      full_name: full_name || "",
    });

    // Load the complete user profile in the background.
    // If /me fails, the login remains successful.
    api
      .getMe()
      .then((r) => {
        if (r?.data) {
          setUser(r.data);
        }
      })
      .catch(() => {
        // Ignore /me failure because login already succeeded.
      });

    return res.data;
  };

  const refreshUser = () =>
    api.getMe().then((r) => {
      setUser(r.data);
      return r.data;
    });

  const doLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("full_name");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login: doLogin,
        logout: doLogout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return ctx;
}

