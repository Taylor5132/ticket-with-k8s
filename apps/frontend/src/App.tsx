import React from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { LogOut, Ticket } from "lucide-react";
import { useAuth } from "./auth";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Detail from "./pages/Detail";
import Seats from "./pages/Seats";
import BookingStatus from "./pages/BookingStatus";
import MyPage from "./pages/MyPage";

export default function App() {
  const { user, logout } = useAuth();
  return (
    <>
      <header className="topbar">
        <div className="topbarInner">
          <Link to="/" className="brand"><Ticket size={22} /> 티켓랩</Link>
          <nav>
            <NavLink to="/" end>공연</NavLink>
          </nav>
          <div className="topbarRight">
            {user ? (
              <>
                <span className="userName">{user.display_name}</span>
                <Link to="/mypage" className="userAvatar" title="마이페이지" aria-label="마이페이지">
                  {user.display_name.slice(0, 1)}
                </Link>
                <button className="iconBtn" onClick={logout} title="로그아웃" aria-label="로그아웃"><LogOut size={16} /></button>
              </>
            ) : (
              <Link to="/login" className="loginLink">로그인</Link>
            )}
          </div>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/login" element={<Login />} />
          <Route path="/performances/:id" element={<Detail />} />
          <Route path="/performances/:id/seats" element={<Seats />} />
          <Route path="/booking" element={<BookingStatus />} />
          <Route path="/mypage" element={<MyPage />} />
        </Routes>
      </main>
      <footer className="siteFooter">
        <div className="siteFooterInner">
          <strong>티켓랩test123</strong>
          <span>Kubernetes 마이크로서비스 팀 프로젝트 데모입니다. 실제 예매 및 결제가 이루어지지 않습니다.</span>
          <span>공연 정보 출처: KOPIS 공연예술통합전산망</span>
        </div>
      </footer>
    </>
  );
}
