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

type Tab = "login" | "signup";

export default function Login() {
  const { user, login, localLogin, signup, googleLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [tab, setTab] = useState<Tab>("login");

  // login fields
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");

  // signup fields
  const [signupId, setSignupId] = useState("");
  const [signupPw, setSignupPw] = useState("");
  const [signupPwConfirm, setSignupPwConfirm] = useState("");
  const [signupName, setSignupName] = useState("");

  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (user) navigate(from, { replace: true }); }, [user]);
  useEffect(() => { setError(""); }, [tab]);

  const submitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginId.trim()) return setError("아이디를 입력해 주세요.");
    if (!password) return setError("비밀번호를 입력해 주세요.");
    setError(""); setSubmitting(true);
    try {
      await localLogin(loginId.trim(), password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message ?? "로그인에 실패했습니다.");
      setSubmitting(false);
    }
  };

  const submitSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signupId.trim()) return setError("아이디를 입력해 주세요.");
    if (!/^[a-zA-Z0-9_]{4,20}$/.test(signupId)) return setError("아이디는 4~20자 영문·숫자·밑줄만 사용할 수 있습니다.");
    if (signupPw.length < 8) return setError("비밀번호는 8자 이상이어야 합니다.");
    if (signupPw !== signupPwConfirm) return setError("비밀번호가 일치하지 않습니다.");
    if (!signupName.trim()) return setError("닉네임을 입력해 주세요.");
    setError(""); setSubmitting(true);
    try {
      await signup(signupId.trim(), signupPw, signupName.trim());
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message ?? "회원가입에 실패했습니다.");
      setSubmitting(false);
    }
  };

  const submitGoogle = async () => {
    setError(""); setSubmitting(true);
    try {
      const finished = await googleLogin();
      if (finished) navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message ?? "Google 로그인에 실패했습니다.");
      setSubmitting(false);
    }
  };

  return (
    <section className="loginPage">
      <div className="loginCard">
        <Link to="/" className="loginBrand"><Ticket size={26} /> 티켓랩</Link>

        <div className="loginTabs">
          <button type="button" className={tab === "login" ? "loginTab active" : "loginTab"} onClick={() => setTab("login")}>로그인</button>
          <button type="button" className={tab === "signup" ? "loginTab active" : "loginTab"} onClick={() => setTab("signup")}>회원가입</button>
        </div>

        {tab === "login" ? (
          <>
            <form className="loginForm" onSubmit={submitLogin} noValidate>
              <label className="field">
                <span className="fieldLabel">아이디</span>
                <input type="text" value={loginId} autoComplete="username" placeholder="아이디를 입력해 주세요" onChange={(e) => setLoginId(e.target.value)} />
              </label>
              <label className="field">
                <span className="fieldLabel">비밀번호</span>
                <input type="password" value={password} autoComplete="current-password" placeholder="비밀번호를 입력해 주세요" onChange={(e) => setPassword(e.target.value)} />
              </label>
              {error && <p className="fieldError" role="alert">{error}</p>}
              <button type="submit" className="loginSubmit" disabled={submitting}>{submitting ? "로그인 중..." : "로그인"}</button>
            </form>

            <div className="loginDivider"><span>또는</span></div>

            <button className="googleBtn" onClick={submitGoogle} disabled={submitting}>
              <GoogleMark /> Google로 시작하기
            </button>

            <div className="demoBox">
              <p className="demoTitle">데모 계정으로 체험해 보세요</p>
              <div className="demoChips">
                {DEMO_ACCOUNTS.map((acc) => (
                  <button key={acc.loginId} type="button" className="demoChip"
                    onClick={async () => { setError(""); setSubmitting(true); try { await login(acc.loginId); navigate(from, { replace: true }); } catch (err: any) { setError(err.message); setSubmitting(false); } }}>
                    <strong>{acc.label}</strong>
                    <span>{acc.desc}</span>
                  </button>
                ))}
              </div>
              <p className="demoNote">데모 환경에서는 비밀번호 검증 없이 아이디 기준으로 로그인됩니다.</p>
            </div>
          </>
        ) : (
          <form className="loginForm" onSubmit={submitSignup} noValidate>
            <label className="field">
              <span className="fieldLabel">아이디</span>
              <input type="text" value={signupId} autoComplete="username" placeholder="4~20자 영문·숫자·밑줄" onChange={(e) => setSignupId(e.target.value)} />
            </label>
            <label className="field">
              <span className="fieldLabel">비밀번호</span>
              <input type="password" value={signupPw} autoComplete="new-password" placeholder="8자 이상" onChange={(e) => setSignupPw(e.target.value)} />
            </label>
            <label className="field">
              <span className="fieldLabel">비밀번호 확인</span>
              <input type="password" value={signupPwConfirm} autoComplete="new-password" placeholder="비밀번호를 다시 입력해 주세요" onChange={(e) => setSignupPwConfirm(e.target.value)} />
            </label>
            <label className="field">
              <span className="fieldLabel">닉네임</span>
              <input type="text" value={signupName} autoComplete="nickname" placeholder="앱에서 표시될 이름" onChange={(e) => setSignupName(e.target.value)} />
            </label>
            {error && <p className="fieldError" role="alert">{error}</p>}
            <p className="signupWelcome">가입 즉시 <strong>10만 포인트</strong>를 드립니다 🎉</p>
            <button type="submit" className="loginSubmit" disabled={submitting}>{submitting ? "가입 중..." : "회원가입"}</button>
          </form>
        )}
      </div>
    </section>
  );
}
