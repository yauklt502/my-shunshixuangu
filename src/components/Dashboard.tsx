"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { EventFeed } from "@/components/EventFeed";
import { IndexBar } from "@/components/IndexBar";
import { SectorColumn } from "@/components/SectorColumn";
import { diffSnapshots } from "@/lib/events";
import { beijingClock } from "@/lib/format";
import { pollIntervalMs, sessionLabel } from "@/lib/market-hours";
import type { MarketSnapshot, SectorSort, Universe, WatchEvent } from "@/lib/types";

const UNIVERSE_OPTIONS: { id: Universe; label: string }[] = [
  { id: "all", label: "综合" },
  { id: "concept", label: "概念" },
  { id: "industry", label: "行业" },
];

const SORT_OPTIONS: { id: SectorSort; label: string }[] = [
  { id: "change", label: "涨幅" },
  { id: "limitUp", label: "涨停数" },
  { id: "amount", label: "成交额" },
  { id: "inflow", label: "主力净流入" },
];

async function loadSnapshot(universe: Universe, sort: SectorSort): Promise<MarketSnapshot> {
  const response = await fetch(`/api/snapshot?universe=${universe}&sort=${sort}`, {
    cache: "no-store",
  });
  const data = (await response.json()) as MarketSnapshot;
  if (!response.ok && !data.sectors) {
    throw new Error(data.error || "行情获取失败");
  }
  return data;
}

function Pill<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { id: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex rounded-full border border-line bg-elev-2 p-0.5">
      {options.map((option) => {
        const active = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            onClick={() => onChange(option.id)}
            className={`rounded-full px-3 py-1 text-xs transition ${
              active ? "bg-gold text-black" : "text-muted hover:text-ink"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function Dashboard() {
  const [universe, setUniverse] = useState<Universe>("all");
  const [sort, setSort] = useState<SectorSort>("change");
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);
  const [events, setEvents] = useState<WatchEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [clock, setClock] = useState(() => beijingClock());
  const prevRef = useRef<MarketSnapshot | null>(null);

  useEffect(() => {
    const id = window.setInterval(() => setClock(beijingClock()), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    prevRef.current = null;

    const pull = async () => {
      try {
        const next = await loadSnapshot(universe, sort);
        if (cancelled) return;
        const fresh = diffSnapshots(prevRef.current, next);
        prevRef.current = next;
        setSnapshot(next);
        if (fresh.length) {
          setEvents((current) => [...fresh, ...current].slice(0, 40));
        }
        setError(next.error ?? null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "行情获取失败");
        }
      }
    };

    const loop = async () => {
      await pull();
      if (cancelled) return;
      const session = prevRef.current?.session ?? "closed";
      timer = window.setTimeout(loop, pollIntervalMs(session));
    };

    void loop();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [universe, sort]);

  const live = snapshot?.session === "auction" || snapshot?.session === "morning" || snapshot?.session === "afternoon";
  const stale =
    snapshot !== null && (snapshot.universe !== universe || snapshot.sort !== sort);
  const loading = snapshot === null || stale;

  const status = useMemo(() => {
    if (!snapshot || stale) return "正在计算前三板块龙头";
    return sessionLabel(snapshot.session);
  }, [snapshot, stale]);

  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-1 flex-col gap-4 px-4 py-4 md:px-6">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs tracking-[0.22em] text-gold">SHUNSHI XUANGU</p>
          <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">顺势选股 · 龙头盯盘</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            自动锁定当日最强三个板块，再按「先封时间 → 连板高度 → 封单」排出龙一、龙二、龙三。统计类连板池已过滤。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 rounded-full border border-line bg-elev px-3 py-1.5 text-xs">
            <span className={`h-2 w-2 rounded-full ${live ? "bg-down pulse-live" : "bg-muted"}`} />
            <span>{status}</span>
            <span className="tabular text-gold">{clock}</span>
          </div>
          <Pill value={universe} options={UNIVERSE_OPTIONS} onChange={setUniverse} />
          <Pill value={sort} options={SORT_OPTIONS} onChange={setSort} />
        </div>
      </header>

      {snapshot ? (
        <IndexBar indices={snapshot.indices} ztCount={snapshot.ztCount} zbCount={snapshot.zbCount} />
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-[84px] animate-pulse rounded-xl bg-elev" />
          ))}
        </div>
      )}

      {error ? (
        <p className="rounded-xl border border-up/30 bg-up/10 px-3 py-2 text-sm text-up">{error}</p>
      ) : null}

      <div className={`grid min-h-[520px] gap-3 lg:grid-cols-3 ${stale ? "opacity-60" : ""}`}>
        {snapshot?.sectors.length
          ? snapshot.sectors.map((sector) => <SectorColumn key={sector.code} sector={sector} />)
          : [1, 2, 3].map((slot) => (
              <div key={slot} className="animate-pulse rounded-2xl border border-line bg-elev/70 p-4">
                <div className="h-6 w-32 rounded bg-elev-2" />
                <div className="mt-4 h-24 rounded-xl bg-elev-2" />
                <div className="mt-2 h-24 rounded-xl bg-elev-2" />
                <div className="mt-2 h-24 rounded-xl bg-elev-2" />
                <p className="mt-4 text-center text-sm text-muted">{loading ? "正在计算前三板块龙头…" : "暂无板块"}</p>
              </div>
            ))}
      </div>

      <EventFeed events={events} tradeDate={snapshot?.tradeDate ?? ""} />

      <details className="rounded-2xl border border-line bg-elev/60 p-4 text-sm text-muted">
        <summary className="cursor-pointer text-ink">龙一 / 龙二 / 龙三怎么定</summary>
        <ol className="mt-3 list-decimal space-y-1.5 pl-5">
          <li>先在概念+行业里取当日最强三个板块（可改成只看概念或行业，也可按涨停数/成交额/主力净流入排序）。</li>
          <li>剔除「昨日连板、历史新高」这类统计池，避免假热点。</li>
          <li>板块内涨停股优先：谁先封谁就是龙一，时间相同看连板，再看封单。</li>
          <li>没有涨停时，按涨幅、成交额排龙一龙二龙三。ST 不参与。</li>
          <li>行情来自东方财富公开接口，盘中约 5 秒刷新，收盘后自动放慢。</li>
        </ol>
      </details>

      <p className="pb-4 text-center text-[11px] text-muted">
        数据仅供盯盘研究，不构成投资建议。点击股票名可跳转东方财富分时。
      </p>
    </div>
  );
}
