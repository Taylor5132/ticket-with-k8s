import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { PerformanceSummary } from "./types";
import { formatPeriod } from "./format";

const PINNED_IDS: string[] = ["72", "31", "89", "25", "71"];

export function Banner({ items }: { items: PerformanceSummary[] }) {
  const [idx, setIdx] = useState(0);
  const list = useMemo(
    () => PINNED_IDS.map((id) => items.find((i) => i.id === id)).filter(Boolean) as PerformanceSummary[],
    [items],
  );
  useEffect(() => {
    if (list.length === 0) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % list.length), 5000);
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
          <p className="bannerDate">{formatPeriod(item.start_date, item.end_date)}</p>
          <Link className="bannerBtn" to={`/performances/${item.id}`}>자세히 보기</Link>
        </div>
        <div className="bannerControls">
          <span className="bannerPage">{idx + 1} / {list.length}</span>
          <button className="bannerNav" aria-label="이전 배너" onClick={() => setIdx((i) => (i - 1 + list.length) % list.length)}><ChevronLeft size={16} /></button>
          <button className="bannerNav" aria-label="다음 배너" onClick={() => setIdx((i) => (i + 1) % list.length)}><ChevronRight size={16} /></button>
        </div>
      </div>
    </div>
  );
}

export function PerformanceCardView({ item }: { item: PerformanceSummary }) {
  return (
    <Link className="posterCard" to={`/performances/${item.id}`}>
      <div className="posterWrap">
        <img src={item.poster_url ?? ""} alt={item.title} loading="lazy" />
        {item.status === "공연예정" && <span className="posterBadge">오픈예정</span>}
      </div>
      <strong className="posterTitle">{item.title}</strong>
      <span className="posterVenue">{item.venue_name}</span>
      <span className="posterDate">{formatPeriod(item.start_date, item.end_date)}</span>
    </Link>
  );
}

/** 가로 스크롤 한 줄 배치. 넘치면 좌우 화살표로 스크롤. */
export function PosterRow({ title, items }: { title: string; items: PerformanceSummary[] }) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const scrollBy = (dir: 1 | -1) => {
    const el = scrollerRef.current;
    if (el) el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: "smooth" });
  };
  return (
    <section className="band">
      <div className="bandHead">
        <h2>{title}</h2>
        {items.length > 0 && (
          <div className="rowArrows">
            <button className="rowArrow" aria-label="왼쪽으로 스크롤" onClick={() => scrollBy(-1)}><ChevronLeft size={18} /></button>
            <button className="rowArrow" aria-label="오른쪽으로 스크롤" onClick={() => scrollBy(1)}><ChevronRight size={18} /></button>
          </div>
        )}
      </div>
      {items.length ? (
        <div className="rowScroller" ref={scrollerRef}>
          {items.map((item) => <PerformanceCardView key={item.id} item={item} />)}
        </div>
      ) : (
        <p className="empty">표시할 공연이 없습니다.</p>
      )}
    </section>
  );
}

export function GridSection({ title, count, items, children }: {
  title: string;
  count?: number;
  items: PerformanceSummary[];
  children?: React.ReactNode;
}) {
  return (
    <section className="band">
      <div className="bandHead">
        <h2>{title}{typeof count === "number" && <span className="bandCount">{count}</span>}</h2>
        {children}
      </div>
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
