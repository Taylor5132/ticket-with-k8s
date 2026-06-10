import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Ticket } from "lucide-react";
import { useAuth } from "../auth";

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

const DEMO_ACCOUNTS = [
  { loginId: "demo-basic", label: "demo-basic", desc: "100,000P" },
  { loginId: "demo-rich", label: "demo-rich", desc: "300,000P" },
];

export default function Login() {
  const { user, login, googleLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) navigate(from, { replace: true });
  }, [user]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginId.trim()) return setError("아이디를 입력해 주세요.");
    if (!password) return setError("비밀번호를 입력해 주세요.");
    setError("");
    setSubmitting(true);
    try {
      await login(loginId.trim());
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message ?? "로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.");
      setSubmitting(false);
    }
  };

  const submitGoogle = async () => {
    setError("");
    setSubmitting(true);
    try {
      const finished = await googleLogin();
      if (finished) navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message ?? "Google 로그인에 실패했습니다. 다시 시도해 주세요.");
      setSubmitting(false);
    }
  };

  return (
    <section className="loginPage">
      <div className="loginCard">
        <Link to="/" className="loginBrand"><Ticket size={26} /> 티켓랩</Link>

        <form className="loginForm" onSubmit={submit} noValidate>
          <label className="field">
            <span className="fieldLabel">아이디</span>
            <input
              type="text"
              value={loginId}
              autoComplete="username"
              placeholder="아이디를 입력해 주세요"
              onChange={(e) => setLoginId(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="fieldLabel">비밀번호</span>
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              placeholder="비밀번호를 입력해 주세요"
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <p className="fieldError" role="alert">{error}</p>}
          <button type="submit" className="loginSubmit" disabled={submitting}>
            {submitting ? "로그인 중..." : "로그인"}
          </button>
        </form>

        <div className="loginDivider"><span>또는</span></div>

        <button className="googleBtn" onClick={submitGoogle} disabled={submitting}>
          <GoogleMark /> Google로 시작하기
        </button>

        <div className="demoBox">
          <p className="demoTitle">데모 계정으로 체험해 보세요</p>
          <div className="demoChips">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.loginId}
                type="button"
                className="demoChip"
                onClick={() => { setLoginId(acc.loginId); setPassword("demo1234"); setError(""); }}
              >
                <strong>{acc.label}</strong>
                <span>{acc.desc}</span>
              </button>
            ))}
          </div>
          <p className="demoNote">데모 환경에서는 비밀번호 검증 없이 아이디 기준으로 로그인됩니다.</p>
        </div>
      </div>
    </section>
  );
}
