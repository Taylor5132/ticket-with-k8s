import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import type { Seat } from "../types";
import { formatShowDate } from "../format";

const gradeClass: Record<string, string> = { VIP: "vip", R: "r-grade", S: "s-grade", A: "a-grade" };
const GRADE_LEGEND = [
  { grade: "VIP", label: "VIP석", price: "150,000원" },
  { grade: "R", label: "R석", price: "120,000원" },
  { grade: "S", label: "S석", price: "90,000원" },
  { grade: "A", label: "A석", price: "60,000원" },
];

type QueueState = { position: number; total: number; initial: number } | null;

function QueueWaiting({ position, total, initial }: { position: number; total: number; initial: number }) {
  const progress = initial > 1 ? Math.min(((initial - position) / (initial - 1)) * 100, 99) : 0;
  return (
    <div className="queueWrap">
      <p className="queueTitle">나의 대기순서</p>
      <p className="queueNum">{position.toLocaleString()}</p>
      <div className="queueBar">
        <div className="queueBarFill" style={{ width: `${progress}%` }} />
      </div>
      <p className="queueMsg">현재 접속 인원이 많아 대기중입니다.<br />잠시만 기다려주시면 예매하기 페이지로 연결됩니다.</p>
      <p className="queueWarn">⚠ 새로고침 하거나 재접속 하시면<br />대기순서가 초기화되어 대기시간이 더 길어집니다.</p>
    </div>
  );
}

export default function Seats() {
  const { id = "" } = useParams();
  const [searchParams] = useSearchParams();
  const showDate = searchParams.get("show_date") ?? "";
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = useAuth();

  const [queue, setQueue] = useState<QueueState>(null);
  const [queueChecked, setQueueChecked] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [perfTitle, setPerfTitle] = useState("");
  const [seats, setSeats] = useState<Seat[]>([]);
  const [selected, setSelected] = useState<Seat[]>([]);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);

  // Step 1: join queue on mount (only when logged in)
  useEffect(() => {
    if (!showDate || !token) { setQueueChecked(true); return; }
    api<{ position: number; total: number }>(
      `/api/queue/join?performance_id=${id}&show_date=${showDate}`,
      token,
      { method: "POST" }
    ).then(({ position, total }) => {
      if (position > 1) {
        setQueue({ position, total, initial: position });
      }
      setQueueChecked(true);
    }).catch(() => setQueueChecked(true));
  }, []);

  // Step 2: poll while in queue
  useEffect(() => {
    if (!queue || !token) return;
    pollRef.current = setInterval(async () => {
      try {
        const res = await api<{ admitted: boolean; position: number; total: number }>(
          `/api/queue/status?performance_id=${id}&show_date=${showDate}`,
          token
        );
        if (res.admitted) {
          clearInterval(pollRef.current!);
          setQueue(null);
        } else {
          setQueue((prev) => prev ? { ...prev, position: res.position, total: res.total } : null);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(pollRef.current!);
  }, [queue !== null]);

  // Step 3: load seats once queue is cleared
  useEffect(() => {
    if (!queueChecked || queue !== null) return;
    if (!showDate) { setLoading(false); return; }
    Promise.all([
      api<any>(`/api/performances/${id}`),
      api<{ seats: Seat[] }>(`/api/performances/${id}/seat-availability?show_date=${showDate}`),
    ]).then(([perf, seatData]) => {
      setPerfTitle(perf.title);
      setSeats(seatData.seats);
    }).finally(() => setLoading(false));
  }, [queueChecked, queue]);

  const rows = useMemo(() => {
    const map: Record<string, Seat[]> = {};
    for (const s of seats) { (map[s.row] ??= []).push(s); }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [seats]);

  const total = selected.reduce((sum, s) => sum + s.price, 0);

  const book = async () => {
    if (!token) return navigate("/login", { state: { from: location.pathname + location.search } });
    if (selected.length === 0 || !showDate) return;
    setBooking(true);
    try {
      const results = await Promise.all(
        selected.map((seat) =>
          api<{ request_id: string }>("/api/booking-requests", token, {
            method: "POST",
            body: JSON.stringify({ performance_id: id, seat_id: seat.seat_id, show_date: showDate }),
          })
        )
      );
      navigate(`/booking?ids=${results.map((r) => r.request_id).join(",")}`);
    } catch (e: any) {
      alert(e.message);
      setBooking(false);
    }
  };

  if (!showDate) {
    return (
      <section>
        <h1>좌석 선택</h1>
        <p className="empty">날짜가 선택되지 않았습니다. <Link to={`/performances/${id}`}>공연 상세</Link>에서 날짜를 선택해 주세요.</p>
      </section>
    );
  }

  if (!queueChecked) return <section><h1>좌석 선택</h1><p className="loadingMsg">대기열을 확인하는 중입니다...</p></section>;

  if (queue) return <QueueWaiting position={queue.position} total={queue.total} initial={queue.initial} />;

  if (loading) return <section><h1>좌석 선택</h1><p className="loadingMsg">좌석 정보를 불러오는 중입니다...</p></section>;

  return (
    <section>
      <div className="seatsHeader">
        <Link to={`/performances/${id}`} className="backLink"><ChevronLeft size={15} /> 공연 상세로 돌아가기</Link>
        <h1>좌석 선택</h1>
        <p className="seatsMeta">{perfTitle} · {formatShowDate(showDate)}</p>
      </div>

      <div className="seatsLayout">
        <div className="seatMapWrapper">
          <div className="stage">STAGE</div>
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
                    selected.some((s) => s.seat_id === seat.seat_id) ? "selected" : "",
                  ].filter(Boolean).join(" ")}
                  onClick={() => setSelected((prev) =>
                    prev.some((s) => s.seat_id === seat.seat_id)
                      ? prev.filter((s) => s.seat_id !== seat.seat_id)
                      : [...prev, seat]
                  )}
                  title={`${seat.seat_id} · ${seat.grade}석 · ${seat.price.toLocaleString()}원`}
                >
                  {seat.number}
                </button>
              ))}
            </div>
          ))}
        </div>

        <aside className="seatPanel">
          <h2>좌석 등급</h2>
          <ul className="gradeList">
            {GRADE_LEGEND.map((g) => (
              <li key={g.grade}>
                <span className={`gradeDot ${gradeClass[g.grade]}`} />
                <span className="gradeName">{g.label}</span>
                <span className="gradePrice">{g.price}</span>
              </li>
            ))}
            <li><span className="gradeDot occupied" /><span className="gradeName">예매 완료</span></li>
          </ul>

          <h2>선택한 좌석</h2>
          {selected.length > 0 ? (
            <ul className="pickedList">
              {selected.map((s) => (
                <li key={s.seat_id}>
                  <strong>{s.seat_id}</strong>
                  <span>{s.grade}석</span>
                  <span className="pickedPrice">{s.price.toLocaleString()}원</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty">좌석을 선택해 주세요.</p>
          )}

          <div className="seatTotal">
            <span>총 {selected.length}석</span>
            <strong>{total.toLocaleString()}원</strong>
          </div>
          <button className="primary payBtn" onClick={book} disabled={selected.length === 0 || booking}>
            {booking ? "처리 중..." : "결제하기"}
          </button>
        </aside>
      </div>
    </section>
  );
}
