"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { IndexBar } from "@/components/IndexBar";
import { TrendSectorPanel } from "@/components/qushi-longtou/TrendSectorPanel";
import {
  beijingClock,
  beijingYmd,
  dateInputToYmd,
  isTodayYmd,
  ymdToDateInput,
} from "@/lib/format";
import { pollIntervalMs, sessionLabel } from "@/lib/market-hours";
import { CRITERION_HINTS, TREND_CRITERIA, type QushiLongTouSnapshot } from "@/lib/qushi-longtou/types";
import { beijingStamp, savePageScreenshot } from "@/lib/save-screenshot";
import type { SectorSort, Universe } from "@/lib/types";

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

const DATE_KEY = "qslt.tradeDate";

function readStoredDate(): string {
  if (typeof window === "undefined") return beijingYmd();
  const raw = window.localStorage.getItem(DATE_KEY);
  if (raw && /^\d{8}$/.test(raw.replaceAll("-", ""))) {
    return raw.replaceAll("-", "");
  }
  return beijingYmd();
}

async function loadSnapshot(
  universe: Universe,
  sort: SectorSort,
  tradeDate: string,
): Promise<QushiLongTouSnapshot> {
  const params = new URLSearchParams({ universe, sort, source: "eastmoney", date: tradeDate });
  const response = await fetch(`/api/qushi-longtou/snapshot?${params.toString()}`, { cache: "no-store" });
  const text = await response.text();
  try {
    return JSON.parse(text) as QushiLongTouSnapshot;
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

export function QuShiLongTouDashboard() {
  const [universe, setUniverse] = useState<Universe>("all");
  const [sort, setSort] = useState<SectorSort>("change");
  const [snapshot, setSnapshot] = useState<QushiLongTouSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tradeDate, setTradeDate] = useState(() => beijingYmd());
  const [clock, setClock] = useState(() => beijingClock());
  const [shotBusy, setShotBusy] = useState(false);
  const [shotToast, setShotToast] = useState<string | null>(null);
  const captureRef = useRef<HTMLDivElement>(null);
  const replayMode = !isTodayYmd(tradeDate);
  const todayYmd = beijingYmd();

  useEffect(() => {
    setTradeDate(readStoredDate());
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setClock(beijingClock()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const changeTradeDate = (value: string) => {
    const next = dateInputToYmd(value) ?? todayYmd;
    setTradeDate(next);
    window.localStorage.setItem(DATE_KEY, next);
    setSnapshot(null);
  };

  const resetTradeDate = () => {
    setTradeDate(todayYmd);
    window.localStorage.setItem(DATE_KEY, todayYmd);
    setSnapshot(null);
  };

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    let session: QushiLongTouSnapshot["session"] = "closed";

    const pull = async () => {
      try {
        const next = await loadSnapshot(universe, sort, tradeDate);
        if (cancelled) return;
        session = next.session;
        setSnapshot(next);
        setError(next.error ?? null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "行情获取失败");
        }
      }
    };

    const loop = async () => {
      await pull();
      if (cancelled || replayMode) return;
      timer = window.setTimeout(loop, pollIntervalMs(session, "eastmoney"));
    };

    void loop();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [universe, sort, tradeDate, replayMode]);

  const live =
    snapshot?.session === "auction" ||
    snapshot?.session === "morning" ||
    snapshot?.session === "afternoon";
  const stale =
    snapshot !== null &&
    (snapshot.universe !== universe || snapshot.sort !== sort || snapshot.tradeDate !== tradeDate);
  const loading = snapshot === null || stale;

  const status = useMemo(() => {
    if (!snapshot || stale) return replayMode ? "正在加载复盘数据" : "正在筛选趋势龙头";
    if (replayMode) return `复盘 ${ymdToDateInput(snapshot.tradeDate)}`;
    return sessionLabel(snapshot.session);
  }, [snapshot, stale, replayMode]);

  const saveScreenshot = async () => {
    const target = captureRef.current;
    if (!target || shotBusy) return;
    setShotBusy(true);
    const filename = `qslt_${tradeDate}_eastmoney_${universe}_${sort}_${beijingStamp()}.png`;
    try {
      const result = await savePageScreenshot(target, filename);
      if (result.ok) {
        setShotToast(result.path ? `已保存到 ${result.path}` : `已保存 ${result.filename}`);
      } else {
        setShotToast(`已下载 ${filename}（未能写入 screenshots 文件夹：${result.error}）`);
      }
    } catch (err) {
      setShotToast(`截屏失败：${err instanceof Error ? err.message : "未知错误"}`);
    } finally {
      setShotBusy(false);
      window.setTimeout(() => setShotToast(null), 6000);
    }
  };

  return (
    <>
      <div
        ref={captureRef}
        className="mx-auto flex w-full max-w-[1600px] flex-1 flex-col gap-4 px-4 py-4 md:px-6"
      >
        <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs tracking-[0.22em] text-gold">QUSHI LONGTOU</p>
            <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">趋势龙头</h1>
            <p className="mt-1 max-w-2xl text-sm text-muted">
              独立战法：在前三热点板块中，用「方向明确、均线支撑、量价配合、回调浅、板块有配合」五维筛选趋势票，非涨停、沿均线走。
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
            <button
              type="button"
              onClick={() => void saveScreenshot()}
              disabled={shotBusy}
              className="rounded-full border border-line bg-elev px-3 py-1.5 text-xs text-muted hover:text-ink disabled:opacity-55"
              title="保存当前页面截图到本机 screenshots 文件夹"
            >
              {shotBusy ? "截屏中…" : "截屏保存"}
            </button>
          </div>
        </header>

        {replayMode ? (
          <p className="rounded-xl border border-gold/30 bg-gold/10 px-3 py-2 text-sm text-gold">
            复盘模式 · {ymdToDateInput(tradeDate)} · 已暂停自动刷新
          </p>
        ) : null}

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

        <div className={`space-y-4 ${stale ? "opacity-60" : ""}`}>
          {snapshot?.sectors.length
            ? snapshot.sectors.map((sector) => <TrendSectorPanel key={sector.code} sector={sector} />)
            : [1, 2, 3].map((slot) => (
                <div key={slot} className="animate-pulse rounded-2xl border border-line bg-elev/70 p-4">
                  <div className="h-6 w-40 rounded bg-elev-2" />
                  <div className="mt-4 grid gap-2 md:grid-cols-3">
                    {Array.from({ length: 3 }).map((_, index) => (
                      <div key={index} className="h-28 rounded-xl bg-elev-2" />
                    ))}
                  </div>
                  <p className="mt-4 text-center text-sm text-muted">
                    {loading ? "正在按五维条件筛选趋势龙头…" : "暂无板块"}
                  </p>
                </div>
              ))}
        </div>

        <details className="rounded-2xl border border-line bg-elev/60 p-4 text-sm text-muted">
          <summary className="cursor-pointer text-ink">五维怎么筛（第17集战法）</summary>
          <ul className="mt-3 space-y-2">
            {TREND_CRITERIA.map((key) => (
              <li key={key}>
                <span className="text-ink">{key}</span>：{CRITERION_HINTS[key]}
              </li>
            ))}
            <li className="pt-1 text-xs">入选门槛：五维至少满足 3 项，且当日未涨停。</li>
          </ul>
        </details>

        <p className="pb-4 text-center text-[11px] text-muted">
          数据仅供盯盘研究，不构成投资建议。
          <Link href="/" className="ml-2 text-gold hover:underline">
            顺势选股
          </Link>
          <Link href="/longtou88" className="ml-2 text-gold hover:underline">
            龙头88
          </Link>
        </p>
      </div>
      {shotToast ? (
        <div className="fixed bottom-4 right-4 z-50 max-w-[min(420px,calc(100vw-2rem))] rounded-xl border border-[#6eb5ff]/45 bg-elev/95 px-3.5 py-2.5 text-xs text-ink shadow-lg">
          {shotToast}
        </div>
      ) : null}
    </>
  );
}
