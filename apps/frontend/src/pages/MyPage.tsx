import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { providerLabel, useAuth } from "../auth";
import type { PerformanceSummary } from "../types";
import { formatShowDate } from "../format";
import { GridSection } from "../components";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="panel"><h2>{title}</h2>{children}</section>;
}

export default function MyPage() {
  const { token, user } = useAuth();
  const [balance, setBalance] = useState<number | null>(null);
  const [bookings, setBookings] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [saved, setSaved] = useState<PerformanceSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    Promise.all([
      api<{ balance: number }>("/api/payments/me/balance", token).then((d) => setBalance(d.balance)),
      api<{ items: any[] }>("/api/bookings/me", token).then((d) => setBookings(d.items)),
      api<{ items: any[] }>("/api/payments/me/history", token).then((d) => setPayments(d.items)),
      api<{ items: PerformanceSummary[] }>("/api/saved/me", token).then((d) => setSaved(d.items)),
    ]).finally(() => setLoading(false));
  }, [token]);

  if (!token || !user) {
    return (
      <section className="statusPage">
        <h1>마이페이지</h1>
        <p>로그인이 필요한 기능입니다.</p>
        <Link className="button primary" to="/login" state={{ from: "/mypage" }}>로그인하러 가기</Link>
      </section>
    );
  }

  if (loading) return <section><h1>마이페이지</h1><p className="loadingMsg">불러오는 중입니다...</p></section>;

  return (
    <section>
      <h1>마이페이지</h1>

      <div className="profileStrip">
        <div className="profileAvatar">{user.display_name.slice(0, 1)}</div>
        <div className="profileWho">
          <strong>{user.display_name}</strong>
          <span>{providerLabel[user.provider] ?? user.provider} 계정</span>
        </div>
        <div className="profilePoints">
          <span>보유 포인트</span>
          <strong>{(balance ?? 0).toLocaleString()} P</strong>
        </div>
      </div>

      <div className="mypageGrid">
        <Panel title="예매내역">
          {bookings.length ? bookings.map((b) => (
            <div key={b.id} className="historyCard">
              <div className="historyTitle">{b.performance_title}</div>
              <div className="historyMeta">{b.venue_name}</div>
              <div className="historyMeta">{b.seat_id} · {b.seat_grade}석 · <strong>{b.paid_amount.toLocaleString()}원</strong></div>
              <div className="historyMeta historyShowDate">{formatShowDate(b.performance_date)}</div>
              <div className="historyDate">{b.booked_at.slice(0, 10)} 예매</div>
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

      <GridSection title="관심공연" count={saved.length} items={saved} />
    </section>
  );
}
