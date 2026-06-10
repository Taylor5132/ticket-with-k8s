import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { Heart } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import type { PerformanceSummary } from "../types";
import { formatPeriod, formatShowDate } from "../format";

const TABS = [
  { key: "info", label: "상세정보" },
  { key: "price", label: "좌석/가격" },
  { key: "guide", label: "관람안내" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

const GRADE_ROWS = [
  { grade: "VIP석", rows: "A-B열", price: "150,000원" },
  { grade: "R석", rows: "C-D열", price: "120,000원" },
  { grade: "S석", rows: "E-F열", price: "90,000원" },
  { grade: "A석", rows: "G-H열", price: "60,000원" },
];

export default function Detail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = useAuth();
  const [detail, setDetail] = useState<any>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("info");

  useEffect(() => {
    api<any>(`/api/performances/${id}`).then(setDetail);
    setSelectedDate(null);
    setTab("info");
  }, [id]);

  useEffect(() => {
    if (!token) { setSaved(false); return; }
    api<{ items: PerformanceSummary[] }>("/api/saved/me", token)
      .then((d) => setSaved(d.items.some((i) => i.id === id)))
      .catch(() => {});
  }, [token, id]);

  if (!detail) return <p className="loadingMsg">불러오는 중입니다...</p>;

  const schedules: string[] = detail.schedules ?? [];
  const goLogin = () => navigate("/login", { state: { from: location.pathname + location.search } });

  const toggleSave = async () => {
    if (!token) return goLogin();
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

  const goToSeats = () => {
    if (!selectedDate) return;
    navigate(`/performances/${id}/seats?show_date=${selectedDate}`);
  };

  return (
    <section className="detail">
      <div className="detailTop">
        <img className="poster" src={detail.poster_url} alt={detail.title} />
        <div className="detailInfo">
          <span className="detailGenre">{detail.genre}</span>
          <h1>{detail.title}</h1>
          <dl className="detailFacts">
            <div><dt>공연장</dt><dd>{detail.venue.name} ({detail.venue.province} {detail.venue.district})</dd></div>
            <div><dt>공연 기간</dt><dd>{formatPeriod(detail.start_date, detail.end_date)}</dd></div>
            <div><dt>공연 시간</dt><dd>{detail.runtime || "-"}</dd></div>
            <div><dt>관람 연령</dt><dd>{detail.age_rating || "-"}</dd></div>
          </dl>

          <div className="dateSection">
            <h2>날짜 선택</h2>
            {schedules.length > 0 ? (
              <div className="datePicker">
                {schedules.map((d) => (
                  <button
                    key={d}
                    className={`dateChip${selectedDate === d ? " active" : ""}`}
                    onClick={() => setSelectedDate(selectedDate === d ? null : d)}
                  >
                    {formatShowDate(d)}
                  </button>
                ))}
              </div>
            ) : (
              <p className="empty">예매 가능한 날짜가 없습니다.</p>
            )}
          </div>

          <div className="actions">
            <button onClick={toggleSave} disabled={saving} className={`saveBtn${saved ? " saved" : ""}`}>
              <Heart size={16} fill={saved ? "currentColor" : "none"} />
              {saved ? "관심공연 저장됨" : "관심공연"}
            </button>
            <button className="primary bookBtn" onClick={goToSeats} disabled={!selectedDate}>
              {selectedDate ? "예매하기" : "날짜를 선택해 주세요"}
            </button>
          </div>
        </div>
      </div>

      <div className="detailTabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            className={`detailTab${tab === t.key ? " active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="detailPanel">
        {tab === "info" && (
          <>
            {detail.cast_text && <p className="detailCast"><strong>출연</strong> {detail.cast_text}</p>}
            {detail.intro_image_urls?.length > 0 ? (
              <div className="introImages">
                {detail.intro_image_urls.map((url: string) => <img key={url} src={url} alt="" loading="lazy" />)}
              </div>
            ) : (
              !detail.cast_text && <p className="empty">등록된 상세정보가 없습니다.</p>
            )}
          </>
        )}
        {tab === "price" && (
          <>
            <table className="priceTable">
              <thead>
                <tr><th>좌석 등급</th><th>좌석 위치</th><th>가격</th></tr>
              </thead>
              <tbody>
                {GRADE_ROWS.map((r) => (
                  <tr key={r.grade}>
                    <td>{r.grade}</td>
                    <td>{r.rows}</td>
                    <td className="pricePrice">{r.price}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {detail.price_text && <p className="priceNote">공식 가격 안내: {detail.price_text}</p>}
          </>
        )}
        {tab === "guide" && (
          <p className="guideText">{detail.guidance_text || "등록된 관람 안내가 없습니다."}</p>
        )}
      </div>
    </section>
  );
}
