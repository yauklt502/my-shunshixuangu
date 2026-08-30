"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { IndexBar } from "@/components/IndexBar";
import { SectorRolesPanel } from "@/components/longtou88/SectorRolesPanel";
import {
  beijingClock,
  beijingYmd,
  dateInputToYmd,
  isTodayYmd,
  ymdToDateInput,
} from "@/lib/format";
import { pollIntervalMs, sessionLabel } from "@/lib/market-hours";
import { beijingStamp, savePageScreenshot } from "@/lib/save-screenshot";
import type { LT88Snapshot } from "@/lib/longtou88/types";
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

const DATE_KEY = "lt88.tradeDate";

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
): Promise<LT88Snapshot> {
  const params = new URLSearchParams({ universe, sort, source: "eastmoney", date: tradeDate });
  const response = await fetch(`/api/longtou88/snapshot?${params.toString()}`, { cache: "no-store" });
  const text = await response.text();
  try {
    return JSON.parse(text) as LT88Snapshot;
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

export function LongTou88Dashboard() {
  const [universe, setUniverse] = useState<Universe>("all");
  const [sort, setSort] = useState<SectorSort>("change");
  const [snapshot, setSnapshot] = useState<LT88Snapshot | null>(null);
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
    let session: LT88Snapshot["session"] = "closed";

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
    if (!snapshot || stale) return replayMode ? "正在加载复盘数据" : "正在解析板块角色";
    if (replayMode) return `复盘 ${ymdToDateInput(snapshot.tradeDate)}`;
    return sessionLabel(snapshot.session);
  }, [snapshot, stale, replayMode]);

  const saveScreenshot = async () => {
    const target = captureRef.current;
    if (!target || shotBusy) return;
    setShotBusy(true);
    const filename = `lt88_${tradeDate}_eastmoney_${universe}_${sort}_${beijingStamp()}.png`;
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
    <div ref={captureRef} className="mx-auto flex w-full max-w-[1600px] flex-1 flex-col gap-4 px-4 py-4 md:px-6">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs tracking-[0.22em] text-gold">LONGTOU 88</p>
          <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">龙头88</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            锁定当日前三热点板块，按「连板龙头 → 趋势龙头 → 中军 → 跟风 → 补涨 → 卡位」六类角色拆解完整板块行情。
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
          ? snapshot.sectors.map((sector) => <SectorRolesPanel key={sector.code} sector={sector} />)
          : [1, 2, 3].map((slot) => (
              <div key={slot} className="animate-pulse rounded-2xl border border-line bg-elev/70 p-4">
                <div className="h-6 w-40 rounded bg-elev-2" />
                <div className="mt-4 grid gap-2 md:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, index) => (
                    <div key={index} className="h-28 rounded-xl bg-elev-2" />
                  ))}
                </div>
                <p className="mt-4 text-center text-sm text-muted">
                  {loading ? "正在计算板块六类角色…" : "暂无板块"}
                </p>
              </div>
            ))}
      </div>

      <details className="rounded-2xl border border-line bg-elev/60 p-4 text-sm text-muted">
        <summary className="cursor-pointer text-ink">六类角色怎么分</summary>
        <ol className="mt-3 list-decimal space-y-1.5 pl-5">
          <li>连板龙头：板块内涨停股优先，按先封时间 → 连板高度 → 封单排序。</li>
          <li>趋势龙头：未涨停但涨幅领先（约 ≥4.5%），趋势最强。</li>
          <li>中军：成交额最大，给板块提供容量。</li>
          <li>跟风：涨幅居中（约 2.5%–9.8%），跟随龙头。</li>
          <li>补涨：低位正涨幅（约 0.3%–2.5%），接溢出情绪。</li>
          <li>卡位：炸板或多次开板的标的，龙头走弱时分歧中出现。</li>
        </ol>
      </details>

      <p className="pb-4 text-center text-[11px] text-muted">
        数据仅供盯盘研究，不构成投资建议。
        <Link href="/" className="ml-2 text-gold hover:underline">
          返回顺势选股
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
