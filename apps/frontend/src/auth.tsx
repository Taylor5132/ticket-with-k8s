import React, { createContext, useContext, useEffect, useState } from "react";
import type { User } from "./types";

export const GOOGLE_OAUTH_ENABLED = import.meta.env.VITE_GOOGLE_OAUTH_ENABLED === "true";

export const providerLabel: Record<string, string> = { dev: "데모", kakao: "카카오", google: "Google" };

const DEMO_NAMES: Record<string, string> = {
  "demo-basic": "기본 데모 사용자",
  "demo-rich": "포인트 많은 데모 사용자",
};

type AuthValue = {
  token: string;
  user: User | null;
  login: (loginId: string) => Promise<void>;
  localLogin: (loginId: string, password: string) => Promise<void>;
  signup: (loginId: string, password: string, displayName: string) => Promise<void>;
  /** 반환값이 true면 리다이렉트 없이 이 자리에서 로그인이 끝난 것 (OAuth 비활성 폴백) */
  googleLogin: () => Promise<boolean>;
  logout: () => void;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState(localStorage.getItem("token") ?? "");
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem("user");
    try { return raw ? JSON.parse(raw) : null; } catch { return null; }
  });

  const saveSession = (accessToken: string, nextUser: User) => {
    localStorage.setItem("token", accessToken);
    localStorage.setItem("user", JSON.stringify(nextUser));
    setToken(accessToken);
    setUser(nextUser);
  };

  // Google OAuth 리다이렉트 후 URL 파라미터로 전달된 토큰 처리
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tokenParam = params.get("token");
    const userParam = params.get("user");
    const oauthError = params.get("oauth_error");
    if (oauthError) {
      alert("Google 로그인에 실패했습니다. 다시 시도해 주세요.");
      window.history.replaceState({}, "", window.location.pathname);
      return;
    }
    if (tokenParam && userParam) {
      try {
        saveSession(tokenParam, JSON.parse(decodeURIComponent(userParam)));
      } catch {}
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const devLogin = async (provider: string, loginId: string) => {
    const response = await fetch("/api/auth/dev-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, login_id: loginId, display_name: DEMO_NAMES[loginId] ?? loginId }),
    });
    if (!response.ok) throw new Error("로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.");
    const data = await response.json();
    saveSession(data.access_token, data.user);
  };

  const login = (loginId: string) => devLogin("dev", loginId);

  const localLogin = async (loginId: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login_id: loginId, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail?.message ?? "로그인에 실패했습니다.");
    }
    const data = await res.json();
    saveSession(data.access_token, data.user);
  };

  const signup = async (loginId: string, password: string, displayName: string) => {
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login_id: loginId, password, display_name: displayName }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail?.message ?? "회원가입에 실패했습니다.");
    }
    const data = await res.json();
    saveSession(data.access_token, data.user);
  };

  const googleLogin = async () => {
    if (GOOGLE_OAUTH_ENABLED) {
      window.location.href = "/api/auth/google";
      return false;
    }
    await devLogin("google", "demo-rich");
    return true;
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken("");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, login, localLogin, signup, googleLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
