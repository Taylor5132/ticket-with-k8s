import React, { useCallback, useEffect, useRef, useState } from "react";
import { RotateCcw } from "lucide-react";
import { api } from "../api";
import type { PerformanceSummary } from "../types";
import { Banner, GridSection, PosterRow } from "../components";

type CountedOption = [name: string, count: number];
const PAGE = 24;

/** 오늘 자정 기준 남은 일수. 내일이면 1, 모레면 2. */
function dDay(dateStr: string): number {
  const [y, m, d] = dateStr.split("-").map(Number);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((new Date(y, m - 1, d).getTime() - today.getTime()) / 86_400_000);
}

function FilterGroup({ label, options, total, current, onChange }: {
  label: string;
  options: CountedOption[];
  total: number;
  current: string | null;
  onChange: (v: string | null) => void;
}) {
  return (
    <div className="filterGroup">
      <h3>{label}</h3>
      <ul>
        <li>
          <button className={`filterItem${!current ? " active" : ""}`} onClick={() => onChange(null)}>
            전체 <span className="filterCount">{total}</span>
          </button>
        </li>
        {options.map(([name, count]) => (
          <li key={name}>
            <button
              className={`filterItem${current === name ? " active" : ""}`}
              onClick={() => onChange(current === name ? null : name)}
            >
              {name} <span className="filterCount">{count}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

type Facets = { total: number; genres: CountedOption[]; areas: CountedOption[] };

export default function Dashboard() {
  const [genre, setGenre] = useState<string | null>(null);
  const [area, setArea] = useState<string | null>(null);
  const [facets, setFacets] = useState<Facets>({ total: 0, genres: [], areas: [] });
  const [upcoming, setUpcoming] = useState<PerformanceSummary[]>([]);
  const [items, setItems] = useState<PerformanceSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // Filter facets (genre/area counts) + catalog total — computed server-side,
  // fetched once. Replaces the old client-side countBy over the full catalog.
  useEffect(() => {
    api<{ total: number; genres: { name: string; count: number }[]; areas: { name: string; count: number }[] }>(
      "/api/performances/facets",
    )
      .then((d) =>
        setFacets({
          total: d.total,
          genres: d.genres.map((g) => [g.name, g.count] as CountedOption),
          areas: d.areas.map((a) => [a.name, a.count] as CountedOption),
        }),
      )
      .catch(() => {});
  }, []);

  const queryFor = useCallback(
    (offset: number) => {
      const p = new URLSearchParams();
      if (genre) p.set("genre", genre);
      if (area) p.set("area", area);
      p.set("limit", String(PAGE));
      p.set("offset", String(offset));
      return p.toString();
    },
    [genre, area],
  );

  // Reset and load the first page (+ "오픈 예정") whenever the filter changes.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setItems([]);
    api<{ items: PerformanceSummary[]; total: number }>(`/api/performances?${queryFor(0)}`)
      .then((d) => {
        if (cancelled) return;
        setItems(d.items);
        setTotal(d.total);
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setTotal(0);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    const up = new URLSearchParams();
    if (genre) up.set("genre", genre);
    if (area) up.set("area", area);
    api<{ items: PerformanceSummary[] }>(`/api/performances/upcoming?${up.toString()}`)
      .then((d) => { if (!cancelled) setUpcoming(d.items); })
      .catch(() => { if (!cancelled) setUpcoming([]); });

    return () => { cancelled = true; };
  }, [genre, area, queryFor]);

  // Refs so loadMore keeps one identity per filter but always reads the latest
  // counts — avoids re-creating the IntersectionObserver on every page append.
  const itemsLenRef = useRef(0);
  const totalRef = useRef(0);
  const busyRef = useRef(false);
  itemsLenRef.current = items.length;
  totalRef.current = total;

  const loadMore = useCallback(() => {
    if (busyRef.current || itemsLenRef.current === 0 || itemsLenRef.current >= totalRef.current) return;
    busyRef.current = true;
    setLoadingMore(true);
    api<{ items: PerformanceSummary[]; total: number }>(`/api/performances?${queryFor(itemsLenRef.current)}`)
      .then((d) => setItems((cur) => [...cur, ...d.items]))
      .catch(() => {})
      .finally(() => {
        busyRef.current = false;
        setLoadingMore(false);
      });
  }, [queryFor]);

  // Infinite scroll via a CALLBACK ref (not useEffect): the sentinel only
  // mounts after the first page loads, and a [loadMore]-deps effect would not
  // re-run at that moment — so the observer never attached. A callback ref
  // fires exactly when the node mounts/unmounts, so the observer is reliably
  // (re)attached. loadMoreRef keeps the callback stable while always calling
  // the latest loadMore (new filter/offset).
  const loadMoreRef = useRef(loadMore);
  loadMoreRef.current = loadMore;
  const observerRef = useRef<IntersectionObserver | null>(null);
  const setSentinel = useCallback((node: HTMLDivElement | null) => {
    observerRef.current?.disconnect();
    if (!node) return;
    observerRef.current = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMoreRef.current(); },
      { rootMargin: "600px" },
    );
    observerRef.current.observe(node);
  }, []);

  const activeLabels = [genre, area].filter(Boolean).join(" · ");
  const hasMore = items.length < total;

  return (
    <section>
      <Banner />
      <div className="dashboardLayout">
        <aside className="filterSidebar">
          <div className="filterHead">
            <h2>필터</h2>
            {(genre || area) && (
              <button className="filterReset" onClick={() => { setGenre(null); setArea(null); }}>
                <RotateCcw size={13} /> 초기화
              </button>
            )}
          </div>
          <FilterGroup label="장르" options={facets.genres} total={facets.total} current={genre} onChange={setGenre} />
          <FilterGroup label="지역" options={facets.areas} total={facets.total} current={area} onChange={setArea} />
        </aside>

        <div className="dashboardMain">
          <PosterRow title="오픈 예정" items={upcoming} getBadge={(i) => `D-${dDay(i.start_date)}`} />
          {loading && items.length === 0 ? (
            <p className="loadingMsg">공연 목록을 불러오는 중입니다...</p>
          ) : (
            <>
              <GridSection
                title={activeLabels ? `${activeLabels} 공연` : "전체 공연"}
                count={total}
                items={items}
              />
              <div ref={setSentinel} aria-hidden style={{ height: 1 }} />
              {loadingMore && <p className="loadingMsg">더 불러오는 중…</p>}
              {!hasMore && total > 0 && <p className="empty">모든 공연을 불러왔습니다.</p>}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
