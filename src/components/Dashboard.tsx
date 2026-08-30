"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { EventFeed } from "@/components/EventFeed";
import { IndexBar } from "@/components/IndexBar";
import { MarketLeadersBar } from "@/components/MarketLeadersBar";
import { SectorColumn } from "@/components/SectorColumn";
import { diffSnapshots } from "@/lib/events";
import { beijingClock, beijingYmd, dateInputToYmd, isTodayYmd, ymdToDateInput } from "@/lib/format";
import { pollIntervalMs, sessionLabel } from "@/lib/market-hours";
import type { DataSource, MarketSnapshot, SectorSort, Universe, WatchEvent } from "@/lib/types";

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

const SOURCE_OPTIONS: { id: DataSource; label: string }[] = [
  { id: "eastmoney", label: "东方财富" },
  { id: "ths", label: "同花顺" },
  { id: "tdx-local", label: "通达信本地" },
  { id: "tdx-hq", label: "通达信实时" },
];

const SOURCE_KEY = "shunshi.source";
const FUYAO_KEY = "shunshi.fuyaoKey";
const DATE_KEY = "shunshi.tradeDate";

function readStoredDate(): string {
  if (typeof window === "undefined") return beijingYmd();
  const raw = window.localStorage.getItem(DATE_KEY);
  if (raw && /^\d{8}$/.test(raw.replaceAll("-", ""))) {
    return raw.replaceAll("-", "");
  }
  return beijingYmd();
}

function readStoredSource(): DataSource {
  if (typeof window === "undefined") return "eastmoney";
  const raw = window.localStorage.getItem(SOURCE_KEY);
  if (raw === "ths" || raw === "tdx-local" || raw === "tdx-hq" || raw === "eastmoney") return raw;
  return "eastmoney";
}

function readStoredKey(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(FUYAO_KEY)?.trim() ?? "";
}

async function loadSnapshot(
  universe: Universe,
  sort: SectorSort,
  source: DataSource,
  fuyaoKey: string,
  tradeDate: string,
): Promise<MarketSnapshot> {
  const params = new URLSearchParams({
    universe,
    sort,
    source,
    date: tradeDate,
  });
  if (source === "tdx-local") {
    params.set("vipdoc", "E:/new_tdx/vipdoc");
  }
  const response = await fetch(`/api/snapshot?${params.toString()}`, {
      cache: "no-store",
      headers: source === "ths" && fuyaoKey ? { "X-Fuyao-Key": fuyaoKey } : undefined,
    },
  );
  const text = await response.text();
  try {
    return JSON.parse(text) as MarketSnapshot;
  } catch {
    throw new Error(response.ok ? "行情解析失败" : `服务错误 ${response.status}`);
  }
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
  const [source, setSource] = useState<DataSource>("eastmoney");
  const [fuyaoKey, setFuyaoKey] = useState("");
  const [keyDraft, setKeyDraft] = useState("");
  const [showKeyPanel, setShowKeyPanel] = useState(false);
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);
  const [events, setEvents] = useState<WatchEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tradeDate, setTradeDate] = useState(() => beijingYmd());
  const [clock, setClock] = useState(() => beijingClock());
  const prevRef = useRef<MarketSnapshot | null>(null);
  const replayMode = !isTodayYmd(tradeDate);
  const todayYmd = beijingYmd();

  useEffect(() => {
    const storedSource = readStoredSource();
    const storedKey = readStoredKey();
    setSource(storedSource);
    setFuyaoKey(storedKey);
    setKeyDraft(storedKey);
    setTradeDate(readStoredDate());
    if (storedSource === "ths" && !storedKey) setShowKeyPanel(true);
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setClock(beijingClock()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const changeSource = (next: DataSource) => {
    setSource(next);
    window.localStorage.setItem(SOURCE_KEY, next);
    prevRef.current = null;
    setSnapshot(null);
    setEvents([]);
    if (next === "ths" && !readStoredKey()) setShowKeyPanel(true);
  };

  const saveKey = () => {
    const next = keyDraft.trim();
    setFuyaoKey(next);
    if (next) window.localStorage.setItem(FUYAO_KEY, next);
    else window.localStorage.removeItem(FUYAO_KEY);
    setShowKeyPanel(false);
    prevRef.current = null;
    setSnapshot(null);
  };

  const changeTradeDate = (value: string) => {
    const next = dateInputToYmd(value) ?? todayYmd;
    setTradeDate(next);
    window.localStorage.setItem(DATE_KEY, next);
    prevRef.current = null;
    setSnapshot(null);
    setEvents([]);
  };

  const resetTradeDate = () => {
    setTradeDate(todayYmd);
    window.localStorage.setItem(DATE_KEY, todayYmd);
    prevRef.current = null;
    setSnapshot(null);
    setEvents([]);
  };

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    prevRef.current = null;

    const pull = async () => {
      try {
        const next = await loadSnapshot(universe, sort, source, fuyaoKey, tradeDate);
        if (cancelled) return;
        const fresh = diffSnapshots(prevRef.current, next);
        prevRef.current = next;
        setSnapshot(next);
        if (fresh.length) {
          setEvents((current) => [...fresh, ...current].slice(0, 40));
        }
        setError(next.error ?? null);
        if (source === "ths" && next.error?.includes("密匙")) setShowKeyPanel(true);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "行情获取失败");
        }
      }
    };

    const loop = async () => {
      await pull();
      if (cancelled || replayMode) return;
      const session = prevRef.current?.session ?? "closed";
      timer = window.setTimeout(loop, pollIntervalMs(session, source));
    };

    void loop();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [universe, sort, source, fuyaoKey, tradeDate, replayMode]);

  const live = snapshot?.session === "auction" || snapshot?.session === "morning" || snapshot?.session === "afternoon";
  const stale =
    snapshot !== null &&
    (snapshot.universe !== universe ||
      snapshot.sort !== sort ||
      snapshot.source !== source ||
      snapshot.tradeDate !== tradeDate);
  const loading = snapshot === null || stale;

  const status = useMemo(() => {
    if (!snapshot || stale) return replayMode ? "正在加载复盘数据" : "正在计算前三板块龙头";
    if (replayMode) return `复盘 ${ymdToDateInput(snapshot.tradeDate)}`;
    return sessionLabel(snapshot.session);
  }, [snapshot, stale, replayMode]);

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
        <div className="flex flex-wrap items-center justify-end gap-2">
          <div className="flex items-center gap-2 rounded-full border border-line bg-elev px-3 py-1.5 text-xs">
            <span className={`h-2 w-2 rounded-full ${live ? "bg-down pulse-live" : "bg-muted"}`} />
            <span>{status}</span>
            <span className="tabular text-gold">{clock}</span>
          </div>
          <Pill value={universe} options={UNIVERSE_OPTIONS} onChange={setUniverse} />
          <Pill value={sort} options={SORT_OPTIONS} onChange={setSort} />
          <label className="inline-flex items-center gap-1.5 rounded-full border border-line bg-elev px-3 py-1.5 text-xs text-muted">
            复盘
            <input
              type="date"
              className="source-select tabular"
              value={ymdToDateInput(tradeDate)}
              max={ymdToDateInput(todayYmd)}
              onChange={(event) => changeTradeDate(event.target.value)}
            />
          </label>
          {replayMode ? (
            <button
              type="button"
              onClick={resetTradeDate}
              className="rounded-full border border-gold/40 bg-gold/10 px-3 py-1.5 text-xs text-gold hover:bg-gold/20"
            >
              回到今日
            </button>
          ) : null}
          <label className="inline-flex items-center gap-1.5 rounded-full border border-line bg-elev px-3 py-1.5 text-xs text-muted">
            数据源
            <select
              className="source-select"
              value={source}
              onChange={(event) => changeSource(event.target.value as DataSource)}
            >
              {SOURCE_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {source === "ths" ? (
            <button
              type="button"
              onClick={() => setShowKeyPanel((open) => !open)}
              className="rounded-full border border-line bg-elev px-3 py-1.5 text-xs text-muted hover:text-ink"
            >
              {fuyaoKey ? "密匙已保存" : "填写密匙"}
            </button>
          ) : null}
        </div>
      </header>

      {showKeyPanel && source === "ths" ? (
        <div className="rounded-2xl border border-line bg-elev/80 p-4">
          <p className="text-sm text-ink">同花顺密匙只保存在这台电脑的浏览器里，不会写进代码仓库。</p>
          <p className="mt-1 text-xs text-muted">
            在 https://fuyao.aicubes.cn/admin/ 签发，请求头是 X-api-key。周末涨停池可能是空的，板块涨幅仍可看。
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input
              type="password"
              value={keyDraft}
              onChange={(event) => setKeyDraft(event.target.value)}
              placeholder="sk-fuyao-..."
              className="min-w-0 flex-1 rounded-xl border border-line bg-elev-2 px-3 py-2 text-sm text-ink outline-none focus:border-gold"
            />
            <button
              type="button"
              onClick={saveKey}
              className="rounded-xl bg-gold px-4 py-2 text-sm text-black"
            >
              保存并刷新
            </button>
          </div>
        </div>
      ) : null}

      {replayMode ? (
        <p className="rounded-xl border border-gold/30 bg-gold/10 px-3 py-2 text-sm text-gold">
          复盘模式 · {ymdToDateInput(tradeDate)} · 已暂停自动刷新
        </p>
      ) : null}

      {snapshot ? (
        <MarketLeadersBar leaders={snapshot.marketLeaders ?? []} />
      ) : (
        <div className="h-[120px] animate-pulse rounded-2xl border border-line bg-elev/70" />
      )}

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
          <li>
            右上角下拉框切换数据源。东方财富约 5 秒刷新；同花顺约 12 秒；通达信实时约 10 秒。通达信本地读
            E:\new_tdx\vipdoc 日线，盘中请用实时。同花顺/通达信暂无主力净流入。
          </li>
        </ol>
      </details>

      <p className="pb-4 text-center text-[11px] text-muted">
        数据仅供盯盘研究，不构成投资建议。点击股票名可跳转东方财富分时。
      </p>
    </div>
  );
}
