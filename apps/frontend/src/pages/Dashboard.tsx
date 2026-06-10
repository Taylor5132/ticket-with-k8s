import React, { useEffect, useMemo, useState } from "react";
import { RotateCcw } from "lucide-react";
import { api } from "../api";
import type { PerformanceSummary } from "../types";
import { Banner, GridSection, PosterRow } from "../components";

type CountedOption = [name: string, count: number];

/** 오늘 자정 기준 남은 일수. 내일이면 1, 모레면 2. */
function dDay(dateStr: string): number {
  const [y, m, d] = dateStr.split("-").map(Number);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((new Date(y, m - 1, d).getTime() - today.getTime()) / 86_400_000);
}

function countBy(items: PerformanceSummary[], key: (i: PerformanceSummary) => string): CountedOption[] {
  const map = new Map<string, number>();
  for (const item of items) {
    const k = key(item);
    if (k) map.set(k, (map.get(k) ?? 0) + 1);
  }
  return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12);
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

export default function Dashboard() {
  const [items, setItems] = useState<PerformanceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [genre, setGenre] = useState<string | null>(null);
  const [area, setArea] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: PerformanceSummary[] }>("/api/performances")
      .then((data) => setItems(data.items))
      .finally(() => setLoading(false));
  }, []);

  const genreOptions = useMemo(() => countBy(items, (i) => i.genre), [items]);
  const areaOptions = useMemo(() => countBy(items, (i) => i.area), [items]);

  const filtered = useMemo(
    () => items.filter((i) => (!genre || i.genre === genre) && (!area || i.area === area)),
    [items, genre, area],
  );
  const upcoming = useMemo(
    () => filtered
      .filter((i) => {
        if (i.status !== "공연예정") return false;
        const d = dDay(i.start_date);
        return d >= 1 && d <= 3;
      })
      .sort((a, b) => dDay(a.start_date) - dDay(b.start_date)),
    [filtered],
  );

  if (loading) return <section><p className="loadingMsg">공연 목록을 불러오는 중입니다...</p></section>;

  const activeLabels = [genre, area].filter(Boolean).join(" · ");

  return (
    <section>
      <Banner items={items} />
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
          <FilterGroup label="장르" options={genreOptions} total={items.length} current={genre} onChange={setGenre} />
          <FilterGroup label="지역" options={areaOptions} total={items.length} current={area} onChange={setArea} />
        </aside>

        <div className="dashboardMain">
          <PosterRow title="오픈 예정" items={upcoming} getBadge={(i) => `D-${dDay(i.start_date)}`} />
          <GridSection
            title={activeLabels ? `${activeLabels} 공연` : "전체 공연"}
            count={filtered.length}
            items={filtered}
          />
        </div>
      </div>
    </section>
  );
}
