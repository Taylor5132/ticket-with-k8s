import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { Heart, LogOut, Ticket } from "lucide-react";
import "./styles.css";

type User = { id: string; provider: string; login_id: string; display_name: string };
type PerformanceCard = {
  id: string;
  title: string;
  poster_url: string | null;
  venue_name: string;
  area: string;
  genre: string;
  start_date: string;
  end_date: string;
  status: string;
};
type Seat = { seat_id: string; row: string; number: number; grade: string; price: number; status: "AVAILABLE" | "OCCUPIED" };

const providerLabel: Record<string, string> = { dev: "데모", kakao: "카카오", google: "Google" };
const gradeClass: Record<string, string> = { VIP: "vip", R: "r-grade", S: "s-grade", A: "a-grade" };
const gradeLabel: Record<string, string> = { VIP: "VIP석 150,000원", R: "R석 120,000원", S: "S석 90,000원", A: "A석 60,000원" };

function useAuth() {
  const [token, setToken] = useState(localStorage.getItem("token") ?? "");
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem("user");
    try { return raw ? JSON.parse(raw) : null; } catch { return null; }
  });
  const login = async (login_id: "demo-basic" | "demo-rich", provider: "kakao" | "google") => {
    const display_name = login_id === "demo-rich" ? "포인트 많은 데모 사용자" : "기본 데모 사용자";
    try {
      const response = await fetch("/api/auth/dev-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, login_id, display_name }),
      });
      if (!response.ok) throw new Error("로그인에 실패했습니다.");
      const data = await response.json();
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
    } catch (e: any) {
      alert(e.message ?? "로그인에 실패했습니다.");
    }
  };
  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken("");
    setUser(null);
  };
  return { token, user, login, logout };
}

async function api<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error?.detail?.message ?? error?.message ?? "문제가 발생했습니다.");
  }
  return response.json();
}

function App() {
  const auth = useAuth();
  return (
    <BrowserRouter>
      <header className="topbar">
        <Link to="/" className="brand"><Ticket size={22} /> 티켓랩</Link>
        <nav><Link to="/">공연</Link><Link to="/mypage">마이페이지</Link></nav>
        <div className="loginBox">
          {auth.user ? (
            <>
              <span className="userName">{auth.user.display_name}</span>
              <span className="providerTag">{providerLabel[auth.user.provider] ?? auth.user.provider}</span>
              <button className="iconBtn" onClick={auth.logout} title="로그아웃"><LogOut size={16} /></button>
            </>
          ) : (
            <>
              <button className="loginBtn kakao" onClick={() => auth.login("demo-basic", "kakao")}>카카오로 시작하기</button>
              <button className="loginBtn google" onClick={() => auth.login("demo-rich", "google")}>Google로 시작하기</button>
            </>
          )}
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/performances/:id" element={<Detail token={auth.token} />} />
          <Route path="/performances/:id/seats" element={<Seats token={auth.token} />} />
          <Route path="/booking/:requestId" element={<BookingStatus token={auth.token} />} />
          <Route path="/mypage" element={<MyPage token={auth.token} user={auth.user} />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

function Dashboard() {
  const [items, setItems] = useState<PerformanceCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterGenre, setFilterGenre] = useState<string | null>(null);
  const [filterArea, setFilterArea] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: PerformanceCard[] }>("/api/performances")
      .then((data) => setItems(data.items))
      .finally(() => setLoading(false));
  }, []);

  const genres = useMemo(() => [...new Set(items.map((i) => i.genre).filter(Boolean))].slice(0, 10), [items]);
  const areas = useMemo(() => [...new Set(items.map((i) => i.area).filter(Boolean))].slice(0, 10), [items]);

  const filtered = useMemo(
    () => items.filter((i) => (!filterGenre || i.genre === filterGenre) && (!filterArea || i.area === filterArea)),
    [items, filterGenre, filterArea],
  );
  const upcoming = useMemo(() => filtered.filter((i) => i.status === "공연예정").slice(0, 8), [filtered]);

  if (loading) return <section><p className="loadingMsg">공연 목록을 불러오는 중입니다...</p></section>;

  return (
    <section>
      <h1>공연</h1>
      <Section title="오픈 예정" items={upcoming} />
      <FilterBand
        title="장르별 보기"
        values={genres}
        current={filterGenre}
        onChange={(v) => setFilterGenre(v)}
      />
      <FilterBand
        title="지역별 보기"
        values={areas}
        current={filterArea}
        onChange={(v) => setFilterArea(v)}
      />
      <Section
        title={`공연 목록${filterGenre || filterArea ? ` · ${[filterGenre, filterArea].filter(Boolean).join(", ")}` : ""}`}
        items={filtered}
      />
    </section>
  );
}

function FilterBand({
  title,
  values,
  current,
  onChange,
}: {
  title: string;
  values: string[];
  current: string | null;
  onChange: (v: string | null) => void;
}) {
  return (
    <section className="band">
      <h2>{title}</h2>
      <div className="chips">
        <span
          className={`chip${!current ? " active" : ""}`}
          onClick={() => onChange(null)}
        >
          전체
        </span>
        {values.map((v) => (
          <span
            key={v}
            className={`chip${current === v ? " active" : ""}`}
            onClick={() => onChange(current === v ? null : v)}
          >
            {v}
          </span>
        ))}
      </div>
    </section>
  );
}

function Section({ title, items }: { title: string; items: PerformanceCard[] }) {
  return (
    <section className="band">
      <h2>{title}</h2>
      {items.length ? (
        <div className="grid">
          {items.map((item) => <PerformanceCardView key={item.id} item={item} />)}
        </div>
      ) : (
        <p className="empty">표시할 공연이 없습니다.</p>
      )}
    </section>
  );
}

function PerformanceCardView({ item }: { item: PerformanceCard }) {
  return (
    <Link className="card" to={`/performances/${item.id}`}>
      <img src={item.poster_url ?? ""} alt="" loading="lazy" />
      <strong>{item.title}</strong>
      <span>{item.venue_name}</span>
      <small>{item.area} · {item.genre}</small>
      <small>{item.start_date} ~ {item.end_date}</small>
    </Link>
  );
}

function Detail({ token }: { token: string }) {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<any>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api<any>(`/api/performances/${id}`).then(setDetail); }, [id]);

  if (!detail) return <p className="loadingMsg">불러오는 중입니다.</p>;

  const toggleSave = async () => {
    if (!token) return alert("로그인이 필요한 기능입니다.");
    setSaving(true);
    try {
      if (saved) {
        await api(`/api/saved/performances/${id}`, token, { method: "DELETE" });
        setSaved(false);
      } else {
        await api(`/api/saved/performances/${id}`, token, { method: "POST" });
        setSaved(true);
      }
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="detail">
      <img className="poster" src={detail.poster_url} alt="" />
      <div>
        <h1>{detail.title}</h1>
        <p className="detailMeta">{detail.venue.name} · {detail.venue.province} {detail.venue.district}</p>
        <p className="detailMeta">{detail.start_date} ~ {detail.end_date}</p>
        <p className="detailMeta">{detail.genre} · {detail.runtime} · {detail.age_rating}</p>
        <div className="actions">
          <button onClick={toggleSave} disabled={saving} className={saved ? "savedBtn" : ""}>
            <Heart size={16} fill={saved ? "currentColor" : "none"} />
            {saved ? "관심공연 저장됨" : "관심공연"}
          </button>
          <button className="primary" onClick={() => navigate(`/performances/${id}/seats`)}>예매하기</button>
        </div>
        <h2>좌석 / 가격</h2>
        <p>{detail.price_text}</p>
        <h2>관람 안내</h2>
        <p>{detail.guidance_text || "등록된 관람 안내가 없습니다."}</p>
        {detail.intro_image_urls?.length > 0 && (
          <div className="introImages">
            {detail.intro_image_urls.map((url: string) => <img key={url} src={url} alt="" />)}
          </div>
        )}
      </div>
    </section>
  );
}

function Seats({ token }: { token: string }) {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [perfTitle, setPerfTitle] = useState("");
  const [seats, setSeats] = useState<Seat[]>([]);
  const [selected, setSelected] = useState<Seat | null>(null);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    Promise.all([
      api<any>(`/api/performances/${id}`),
      api<{ seats: Seat[] }>(`/api/performances/${id}/seat-availability`),
    ]).then(([perf, seatData]) => {
      setPerfTitle(perf.title);
      setSeats(seatData.seats);
    }).finally(() => setLoading(false));
  }, [id]);

  const rows = useMemo(() => {
    const map: Record<string, Seat[]> = {};
    for (const s of seats) {
      (map[s.row] ??= []).push(s);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [seats]);

  const book = async () => {
    if (!token) return alert("로그인이 필요한 기능입니다.");
    if (!selected) return;
    setBooking(true);
    try {
      const data = await api<{ request_id: string }>("/api/booking-requests", token, {
        method: "POST",
        body: JSON.stringify({ performance_id: id, seat_id: selected.seat_id }),
      });
      navigate(`/booking/${data.request_id}`);
    } catch (e: any) {
      alert(e.message);
      setBooking(false);
    }
  };

  if (loading) return <section><h1>좌석 선택</h1><p className="loadingMsg">좌석 정보를 불러오는 중입니다...</p></section>;

  return (
    <section>
      <div className="seatsHeader">
        <Link to={`/performances/${id}`} className="backLink">← {perfTitle || "공연 상세"}</Link>
        <h1>좌석 선택</h1>
      </div>

      <div className="gradeLegend">
        {Object.entries(gradeLabel).map(([grade, label]) => (
          <span key={grade} className={`legendItem ${gradeClass[grade]}`}>{label}</span>
        ))}
        <span className="legendItem occupied-label">예매완료</span>
      </div>

      <div className="seatMapWrapper">
        <div className="stage">무 대</div>
        {rows.map(([row, rowSeats]) => (
          <div key={row} className="seatRow">
            <span className="rowLabel">{row}</span>
            {rowSeats.map((seat) => (
              <button
                key={seat.seat_id}
                disabled={seat.status === "OCCUPIED"}
                className={[
                  "seat",
                  gradeClass[seat.grade] ?? "",
                  seat.status === "OCCUPIED" ? "occupied" : "available",
                  selected?.seat_id === seat.seat_id ? "selected" : "",
                ].filter(Boolean).join(" ")}
                onClick={() => setSelected(seat)}
                title={`${seat.seat_id} · ${seat.grade}석 · ${seat.price.toLocaleString()}원`}
              >
                {seat.number}
              </button>
            ))}
          </div>
        ))}
      </div>

      <aside className="summary">
        {selected ? (
          <>
            <strong>{selected.seat_id}</strong>
            <span>{selected.grade}석</span>
            <span className="summaryPrice">{selected.price.toLocaleString()}원</span>
          </>
        ) : (
          <span className="summaryHint">좌석을 선택해 주세요.</span>
        )}
      </aside>
      <button className="primary" onClick={book} disabled={!selected || booking}>
        {booking ? "처리 중..." : "결제하기"}
      </button>
    </section>
  );
}

function BookingStatus({ token }: { token: string }) {
  const { requestId = "" } = useParams();
  const [state, setState] = useState<any>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (!requestId || !token) return;
    stoppedRef.current = false;
    const poll = async () => {
      if (stoppedRef.current) return;
      try {
        const data = await api<any>(`/api/booking-requests/${requestId}`, token);
        setState(data);
        if (data.status === "CONFIRMED" || data.status === "FAILED") {
          stoppedRef.current = true;
        }
      } catch {}
    };
    poll();
    const timer = setInterval(poll, 1000);
    return () => { stoppedRef.current = true; clearInterval(timer); };
  }, [requestId, token]);

  const failureMsg: Record<string, string> = {
    SEAT_ALREADY_BOOKED: "이미 예매된 좌석입니다. 다른 좌석을 선택해 주세요.",
    INSUFFICIENT_POINTS: "보유 포인트가 부족합니다. 포인트가 많은 데모 사용자로 로그인해 주세요.",
    PAYMENT_FAILED: "결제 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    WORKER_ERROR: "예매 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
  };

  if (!state || state.status === "PENDING" || state.status === "PROCESSING") {
    return (
      <section className="statusPage">
        <div className="spinner" />
        <h1>예매 처리 중</h1>
        <p>좌석과 포인트를 확인하고 있습니다. 잠시만 기다려 주세요.</p>
      </section>
    );
  }

  if (state.status === "CONFIRMED") {
    return (
      <section className="statusPage">
        <div className="statusIcon success">✓</div>
        <h1>예매 완료</h1>
        <p>예매가 정상적으로 처리되었습니다.</p>
        <div className="statusActions">
          <Link className="button primary" to="/mypage">마이페이지에서 확인</Link>
          <Link className="button" to="/">공연 목록으로</Link>
        </div>
      </section>
    );
  }

  return (
    <section className="statusPage">
      <div className="statusIcon failure">✗</div>
      <h1>예매 실패</h1>
      <p>{failureMsg[state.failure_reason] ?? "알 수 없는 문제로 예매에 실패했습니다."}</p>
      <div className="statusActions">
        <Link className="button primary" to="/">공연 목록으로</Link>
      </div>
    </section>
  );
}

function MyPage({ token, user }: { token: string; user: User | null }) {
  const [balance, setBalance] = useState<number | null>(null);
  const [bookings, setBookings] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [saved, setSaved] = useState<PerformanceCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    Promise.all([
      api<{ balance: number }>("/api/payments/me/balance", token).then((d) => setBalance(d.balance)),
      api<{ items: any[] }>("/api/bookings/me", token).then((d) => setBookings(d.items)),
      api<{ items: any[] }>("/api/payments/me/history", token).then((d) => setPayments(d.items)),
      api<{ items: PerformanceCard[] }>("/api/saved/me", token).then((d) => setSaved(d.items)),
    ]).finally(() => setLoading(false));
  }, [token]);

  if (!token || !user) {
    return (
      <section>
        <h1>마이페이지</h1>
        <p className="empty">로그인이 필요한 기능입니다.</p>
      </section>
    );
  }

  if (loading) return <section><h1>마이페이지</h1><p className="loadingMsg">불러오는 중입니다...</p></section>;

  return (
    <section>
      <h1>마이페이지</h1>
      <div className="mypageGrid">
        <Panel title="내 정보">
          <p className="infoName">{user.display_name}</p>
          <p className="infoProvider">{providerLabel[user.provider] ?? user.provider} 계정</p>
        </Panel>
        <Panel title="보유 포인트">
          <p className="balanceAmount">{(balance ?? 0).toLocaleString()} <span>P</span></p>
        </Panel>
        <Panel title="예매내역">
          {bookings.length ? bookings.map((b) => (
            <div key={b.id} className="historyCard">
              <div className="historyTitle">{b.performance_title}</div>
              <div className="historyMeta">{b.venue_name}</div>
              <div className="historyMeta">{b.seat_id} · {b.seat_grade}석 · <strong>{b.paid_amount.toLocaleString()}원</strong></div>
              <div className="historyDate">{b.booked_at.slice(0, 10)}</div>
            </div>
          )) : <p className="empty">아직 예매내역이 없습니다.</p>}
        </Panel>
        <Panel title="최근 결제내역">
          {payments.length ? payments.map((p) => (
            <div key={p.id} className="historyCard">
              <div className="historyTitle">{p.performance_title}</div>
              <div className="historyMeta"><strong>{p.amount.toLocaleString()}원</strong> · 결제완료</div>
              <div className="historyDate">{p.paid_at.slice(0, 10)}</div>
            </div>
          )) : <p className="empty">아직 결제내역이 없습니다.</p>}
        </Panel>
      </div>
      <Section title="관심공연" items={saved} />
    </section>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="panel"><h2>{title}</h2>{children}</section>;
}

createRoot(document.getElementById("root")!).render(<App />);
