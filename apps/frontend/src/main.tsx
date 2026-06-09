import React, { useEffect, useMemo, useState } from "react";
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

function useAuth() {
  const [token, setToken] = useState(localStorage.getItem("token") ?? "");
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem("user");
    try { return raw ? JSON.parse(raw) : null; } catch { return null; }
  });
  const login = async (login_id: "demo-basic" | "demo-rich", provider: "kakao" | "google") => {
    const display_name = login_id === "demo-rich" ? "포인트 많은 데모 사용자" : "기본 데모 사용자";
    const response = await fetch("/api/auth/dev-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, login_id, display_name }),
    });
    const data = await response.json();
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
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
              <span>{auth.user.display_name}</span>
              <button className="iconBtn" onClick={auth.logout} title="로그아웃"><LogOut size={16} /></button>
            </>
          ) : (
            <>
              <button onClick={() => auth.login("demo-basic", "kakao")}>카카오로 시작하기</button>
              <button onClick={() => auth.login("demo-rich", "google")}>Google로 시작하기</button>
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

// 마음에 드는 공연 ID를 여기에 추가하면 해당 공연만 배너에 표시됨
// 공연 상세 페이지 URL /performances/72 → ID는 "72"
// 비워두면 자동으로 5개 선택
const PINNED_IDS: string[] = ["72", "31", "89", "25", "71"];

function Banner({ items }: { items: PerformanceCard[] }) {
  const [idx, setIdx] = useState(0);
  const list = useMemo(() => {
    return PINNED_IDS.map((id) => items.find((i) => i.id === id)).filter(Boolean) as PerformanceCard[];
  }, [items]);
  useEffect(() => {
    if (list.length === 0) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % list.length), 4000);
    return () => clearInterval(t);
  }, [list.length]);
  if (list.length === 0) return null;
  const item = list[idx];
  return (
    <div className="banner" style={{ backgroundImage: `url(${item.poster_url})` }}>
      <div className="bannerOverlay">
        <div className="bannerContent">
          <span className="bannerGenre">{item.genre}</span>
          <h2 className="bannerTitle">{item.title}</h2>
          <p className="bannerMeta">{item.venue_name} · {item.area}</p>
          <p className="bannerDate">{item.start_date} ~ {item.end_date}</p>
          <Link className="bannerBtn" to={`/performances/${item.id}`}>자세히 보기</Link>
        </div>
        <div className="bannerDots">
          {list.map((_, i) => <button key={i} className={`bannerDot${i === idx ? " active" : ""}`} onClick={() => setIdx(i)} />)}
        </div>
        <button className="bannerArrow bannerArrowL" onClick={() => setIdx((i) => (i - 1 + list.length) % list.length)}>‹</button>
        <button className="bannerArrow bannerArrowR" onClick={() => setIdx((i) => (i + 1) % list.length)}>›</button>
      </div>
    </div>
  );
}

function Dashboard() {
  const [items, setItems] = useState<PerformanceCard[]>([]);
  useEffect(() => { api<{ items: PerformanceCard[] }>("/api/performances").then((data) => setItems(data.items)); }, []);
  const genres = useMemo(() => [...new Set(items.map((item) => item.genre).filter(Boolean))].slice(0, 8), [items]);
  const areas = useMemo(() => [...new Set(items.map((item) => item.area).filter(Boolean))].slice(0, 8), [items]);
  return (
    <section>
      <Banner items={items} />
      <Section title="오픈 예정" items={items.filter((item) => item.status === "공연예정").slice(0, 8)} />
      <FilterRow title="장르별 보기" values={genres} />
      <FilterRow title="지역별 보기" values={areas} />
      <Section title="공연 목록" items={items} />
    </section>
  );
}

function FilterRow({ title, values }: { title: string; values: string[] }) {
  return <section className="band"><h2>{title}</h2><div className="chips">{values.map((v) => <span className="chip" key={v}>{v}</span>)}</div></section>;
}

function Section({ title, items }: { title: string; items: PerformanceCard[] }) {
  return <section className="band"><h2>{title}</h2>{items.length ? <div className="grid">{items.map((item) => <PerformanceCardView key={item.id} item={item} />)}</div> : <p className="empty">표시할 공연이 없습니다.</p>}</section>;
}

function PerformanceCardView({ item }: { item: PerformanceCard }) {
  return (
    <Link className="card" to={`/performances/${item.id}`}>
      <img src={item.poster_url ?? ""} alt="" />
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
  useEffect(() => { api<any>(`/api/performances/${id}`).then(setDetail); }, [id]);
  if (!detail) return <p>불러오는 중입니다.</p>;
  const save = async () => {
    if (!token) return alert("로그인이 필요한 기능입니다.");
    await api(`/api/saved/performances/${id}`, token, { method: "POST" });
    alert("관심공연에 추가했습니다.");
  };
  return (
    <section className="detail">
      <img className="poster" src={detail.poster_url} alt="" />
      <div>
        <h1>{detail.title}</h1>
        <p>{detail.venue.name} · {detail.venue.province} {detail.venue.district}</p>
        <p>{detail.start_date} ~ {detail.end_date}</p>
        <p>{detail.genre} · {detail.runtime} · {detail.age_rating}</p>
        <div className="actions">
          <button onClick={save}><Heart size={16} /> 관심공연</button>
          <button className="primary" onClick={() => navigate(`/performances/${id}/seats`)}>예매하기</button>
        </div>
        <h2>좌석/가격</h2><p>{detail.price_text}</p>
        <h2>관람안내</h2><p>{detail.guidance_text || "등록된 관람 안내가 없습니다."}</p>
        <div className="introImages">{detail.intro_image_urls?.map((url: string) => <img key={url} src={url} alt="" />)}</div>
      </div>
    </section>
  );
}

function Seats({ token }: { token: string }) {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [seats, setSeats] = useState<Seat[]>([]);
  const [selected, setSelected] = useState<Seat | null>(null);
  useEffect(() => { api<{ seats: Seat[] }>(`/api/performances/${id}/seat-availability`).then((data) => setSeats(data.seats)); }, [id]);
  const book = async () => {
    if (!token) return alert("로그인이 필요한 기능입니다.");
    if (!selected) return alert("좌석을 선택해 주세요.");
    const data = await api<{ request_id: string }>("/api/booking-requests", token, { method: "POST", body: JSON.stringify({ performance_id: id, seat_id: selected.seat_id }) });
    navigate(`/booking/${data.request_id}`);
  };
  return (
    <section>
      <h1>좌석 선택</h1>
      <div className="legend"><span>선택 가능</span><span>예매 완료</span><span>선택한 좌석</span></div>
      <div className="seatMap">{seats.map((seat) => <button key={seat.seat_id} disabled={seat.status === "OCCUPIED"} className={`seat ${seat.status.toLowerCase()} ${selected?.seat_id === seat.seat_id ? "selected" : ""}`} onClick={() => setSelected(seat)}>{seat.seat_id}</button>)}</div>
      <aside className="summary">{selected ? <><strong>{selected.seat_id}</strong><span>{selected.grade}석</span><span>{selected.price.toLocaleString()}원</span></> : "좌석을 선택해 주세요."}</aside>
      <button className="primary" onClick={book}>결제하기</button>
    </section>
  );
}

function BookingStatus({ token }: { token: string }) {
  const { requestId = "" } = useParams();
  const [state, setState] = useState<any>(null);
  useEffect(() => {
    const timer = setInterval(() => api<any>(`/api/booking-requests/${requestId}`, token).then(setState), 1000);
    return () => clearInterval(timer);
  }, [requestId, token]);
  const failure: Record<string, string> = {
    SEAT_ALREADY_BOOKED: "이미 예매된 좌석입니다. 다른 좌석을 선택해 주세요.",
    INSUFFICIENT_POINTS: "보유 포인트가 부족합니다. 다른 좌석을 선택하거나 포인트가 많은 데모 사용자로 로그인해 주세요.",
    PAYMENT_FAILED: "결제 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    WORKER_ERROR: "예매 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
  };
  if (!state || state.status === "PENDING" || state.status === "PROCESSING") return <section><h1>예매 요청 처리 중입니다</h1><p>좌석과 포인트를 확인하고 있습니다. 잠시만 기다려 주세요.</p></section>;
  if (state.status === "CONFIRMED") return <section><h1>예매가 완료되었습니다</h1><p>마이페이지에서 예매내역과 결제내역을 확인할 수 있습니다.</p><Link className="button" to="/mypage">마이페이지로 이동</Link></section>;
  return <section><h1>예매에 실패했습니다</h1><p>{failure[state.failure_reason] ?? "알 수 없는 문제로 예매에 실패했습니다."}</p><Link className="button" to="/">공연으로 돌아가기</Link></section>;
}

function MyPage({ token, user }: { token: string; user: User | null }) {
  const [balance, setBalance] = useState<any>(null);
  const [bookings, setBookings] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [saved, setSaved] = useState<PerformanceCard[]>([]);
  useEffect(() => {
    if (!token) return;
    api<any>("/api/payments/me/balance", token).then(setBalance);
    api<any>("/api/bookings/me", token).then((data) => setBookings(data.items));
    api<any>("/api/payments/me/history", token).then((data) => setPayments(data.items));
    api<any>("/api/saved/me", token).then((data) => setSaved(data.items));
  }, [token]);
  if (!token || !user) return <section><h1>마이페이지</h1><p>로그인이 필요한 기능입니다.</p></section>;
  return (
    <section>
      <h1>마이페이지</h1>
      <div className="mypageGrid">
        <Panel title="내 정보"><p>{user.display_name}</p><p>{providerLabel[user.provider] ?? user.provider}</p></Panel>
        <Panel title="보유 포인트"><strong>{(balance?.balance ?? 0).toLocaleString()} P</strong></Panel>
        <Panel title="예매내역">{bookings.length ? bookings.map((b) => <p key={b.id}>{b.performance_title} · {b.seat_id} · {b.paid_amount.toLocaleString()}원</p>) : <p>아직 예매내역이 없습니다.</p>}</Panel>
        <Panel title="최근 결제내역">{payments.length ? payments.map((p) => <p key={p.id}>{p.performance_title} · {p.amount.toLocaleString()}원 · 결제완료</p>) : <p>아직 결제내역이 없습니다.</p>}</Panel>
      </div>
      <Section title="관심공연" items={saved} />
    </section>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="panel"><h2>{title}</h2>{children}</section>;
}

createRoot(document.getElementById("root")!).render(<App />);
