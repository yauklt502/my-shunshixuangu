/**
 * Auction stock overlay: day K on the left + TickFlow EChartsIntraday float on the right.
 * Intraday panel logic/style ported from shy3130/tick-stock-panel (MIT).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { tdxKline, tdxMinute, toTdxCode } from "@/api/tdx";
import { EChartsIntraday, type YMode } from "@/components/tickflow/EChartsIntraday";
import type { MinuteKlineRow, PriceLimitInfo } from "@/components/tickflow/types";

type StockPick = { code: string; name: string };
type DayBar = { time: string; open: number; high: number; low: number; close: number; volume: number };

export function StockChartModal({
  stock,
  date,
  onClose,
}: {
  stock: StockPick;
  date: string;
  onClose: () => void;
}) {
  const tdxCode = toTdxCode(stock.code);
  const marketTag = marketSuffix(stock.code);
  const [yMode, setYMode] = useState<YMode>("adaptive");
  const panelBodyRef = useRef<HTMLDivElement>(null);
  const [chartHeight, setChartHeight] = useState(560);
  const [minute, setMinute] = useState<{
    loading: boolean;
    error: string | null;
    rows: MinuteKlineRow[];
    prevClose: number | null;
    priceLimit: PriceLimitInfo;
  }>({
    loading: true,
    error: null,
    rows: [],
    prevClose: null,
    priceLimit: priceLimitForCode(stock.code),
  });
  const [day, setDay] = useState<{
    loading: boolean;
    error: string | null;
    bars: DayBar[];
  }>({ loading: true, error: null, bars: [] });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [onClose]);

  useEffect(() => {
    const el = panelBodyRef.current;
    if (!el) return;
    const measure = () => setChartHeight(Math.max(280, el.clientHeight - 8));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    let alive = true;
    setMinute((s) => ({
      ...s,
      loading: true,
      error: null,
      rows: [],
      priceLimit: priceLimitForCode(stock.code),
    }));
    const ymd = date.replaceAll("-", "");
    tdxMinute(tdxCode)
      .catch(() => tdxMinute(tdxCode, ymd))
      .then((data) => {
        if (!alive) return;
        setMinute({
          loading: false,
          error: null,
          rows: toMinuteRows(data.points || [], date),
          prevClose: data.prev_close ?? null,
          priceLimit: priceLimitForCode(stock.code),
        });
      })
      .catch((err: Error) => {
        if (!alive) return;
        setMinute({
          loading: false,
          error: err.message || "分时加载失败",
          rows: [],
          prevClose: null,
          priceLimit: priceLimitForCode(stock.code),
        });
      });
    return () => {
      alive = false;
    };
  }, [tdxCode, date, stock.code]);

  useEffect(() => {
    let alive = true;
    setDay({ loading: true, error: null, bars: [] });
    tdxKline(tdxCode, "day", 160)
      .then((data) => {
        if (!alive) return;
        setDay({ loading: false, error: null, bars: data.bars || [] });
      })
      .catch((err: Error) => {
        if (!alive) return;
        setDay({ loading: false, error: err.message || "日K加载失败", bars: [] });
      });
    return () => {
      alive = false;
    };
  }, [tdxCode]);

  const quote = useMemo(() => {
    const lastBar = day.bars[day.bars.length - 1];
    const lastMin = minute.rows[minute.rows.length - 1];
    const prev =
      minute.prevClose && minute.prevClose > 0
        ? minute.prevClose
        : day.bars.length > 1
          ? day.bars[day.bars.length - 2]?.close
          : lastBar?.open;
    const price = lastMin?.close ?? lastBar?.close ?? null;
    if (price == null || !prev || prev <= 0) {
      return { price: null as number | null, chg: null as number | null, pct: null as number | null };
    }
    const chg = price - prev;
    return { price, chg, pct: (chg / prev) * 100 };
  }, [day.bars, minute.rows, minute.prevClose]);

  const panelPrevClose = useMemo(() => {
    if (minute.prevClose && minute.prevClose > 0) return minute.prevClose;
    if (day.bars.length >= 2) return day.bars[day.bars.length - 2].close;
    return undefined;
  }, [minute.prevClose, day.bars]);

  return (
    <div className="tick-stage" role="dialog" aria-modal="true" aria-label={`${stock.name} 行情`}>
      <div className="tick-stage-main">
        <header className="tick-stage-hd">
          <div className="tick-stage-title">
            <span className="tick-code">
              {stock.code}.{marketTag}
            </span>
            <span className="tick-name">{stock.name}</span>
          </div>
          <div className="tick-stage-quote">
            {quote.price != null ? (
              <>
                <b className={toneClass(quote.chg)}>{quote.price.toFixed(2)}</b>
                <span className={toneClass(quote.chg)}>
                  {fmtSigned(quote.chg)} {fmtPct(quote.pct)}
                </span>
              </>
            ) : (
              <span className="faint">行情加载中…</span>
            )}
          </div>
        </header>

        <div className="tick-stage-body">
          {day.loading ? (
            <div className="spinner">正在拉取日K…</div>
          ) : day.error ? (
            <div className="error-box">{day.error}</div>
          ) : day.bars.length ? (
            <DayChart bars={day.bars} />
          ) : (
            <div className="empty">暂无日K</div>
          )}
        </div>
      </div>

      <aside className="tick-panel" aria-label="TICK STOCK PANEL">
        <button
          type="button"
          className="tick-close"
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          aria-label="关闭浮窗"
        >
          ×
        </button>
        <div className="tick-panel-hd">
          <div className="eci-mode-group">
            <button
              type="button"
              className={yMode === "adaptive" ? "eci-mode on" : "eci-mode"}
              onClick={(e) => {
                e.stopPropagation();
                setYMode("adaptive");
              }}
            >
              自适应
            </button>
            <div className="eci-mode-sep" />
            <button
              type="button"
              className={yMode === "limit" ? "eci-mode on" : "eci-mode"}
              onClick={(e) => {
                e.stopPropagation();
                setYMode("limit");
              }}
            >
              涨跌停
            </button>
          </div>
        </div>
        <div className="tick-panel-bd tick-panel-bd-tickflow" ref={panelBodyRef}>
          {minute.loading ? (
            <div className="spinner">正在拉取分时…</div>
          ) : minute.error ? (
            <div className="error-box">{minute.error}</div>
          ) : minute.rows.length ? (
            <EChartsIntraday
              data={minute.rows}
              height={chartHeight}
              prevClose={panelPrevClose}
              date={date}
              priceLimit={minute.priceLimit}
              currentPrice={quote.price ?? undefined}
              yMode={yMode}
              onYModeChange={setYMode}
              hideModeToggle
            />
          ) : (
            <div className="empty">暂无分时</div>
          )}
        </div>
      </aside>
    </div>
  );
}

function DayChart({ bars }: { bars: DayBar[] }) {
  const visible = useMemo(() => bars.slice(-120), [bars]);
  const w = 960;
  const candleH = 460;
  const volH = 110;
  const gap = 8;
  const totalH = candleH + gap + volH;
  const pad = { l: 52, r: 16, t: 18, b: 28 };
  const highs = visible.map((b) => b.high);
  const lows = visible.map((b) => b.low);
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const span = Math.max(max - min, 0.01);
  const plotW = w - pad.l - pad.r;
  const plotH = candleH - pad.t - pad.b;
  const gapX = plotW / visible.length;
  const bodyW = Math.max(2, gapX * 0.62);
  const yAt = (v: number) => pad.t + ((max - v) / span) * plotH;
  const closes = visible.map((b) => b.close);
  const ma = (n: number) =>
    closes.map((_, i) => {
      if (i + 1 < n) return null;
      const slice = closes.slice(i + 1 - n, i + 1);
      return slice.reduce((a, b) => a + b, 0) / n;
    });
  const pathOf = (vals: Array<number | null>) => {
    let started = false;
    return vals
      .map((v, i) => {
        if (v == null) return "";
        const x = pad.l + i * gapX + gapX / 2;
        const y = yAt(v);
        const cmd = started ? "L" : "M";
        started = true;
        return `${cmd}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  };
  const maxVol = Math.max(...visible.map((b) => b.volume || 0), 1);
  const volTop = candleH + gap;
  const volPlotH = volH - 10;
  const first = visible[0];
  const last = visible[visible.length - 1];

  return (
    <svg className="tick-day-chart" viewBox={`0 0 ${w} ${totalH}`} role="img" aria-label="日K线">
      {[0.25, 0.5, 0.75].map((r) => (
        <line
          key={r}
          x1={pad.l}
          y1={pad.t + plotH * r}
          x2={w - pad.r}
          y2={pad.t + plotH * r}
          stroke="rgba(15,23,42,0.06)"
        />
      ))}
      {visible.map((bar, i) => {
        const x = pad.l + i * gapX + gapX / 2;
        const up = bar.close >= bar.open;
        const color = up ? "#e53935" : "#1aa37a";
        const yHigh = yAt(bar.high);
        const yLow = yAt(bar.low);
        const yOpen = yAt(bar.open);
        const yClose = yAt(bar.close);
        const top = Math.min(yOpen, yClose);
        const bodyH = Math.max(1, Math.abs(yClose - yOpen));
        const barH = Math.max(1, (bar.volume / maxVol) * volPlotH);
        return (
          <g key={`${bar.time}-${i}`}>
            <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={color} strokeWidth="1" />
            <rect x={x - bodyW / 2} y={top} width={bodyW} height={bodyH} fill={color} />
            <rect
              x={x - bodyW / 2}
              y={volTop + (volPlotH - barH)}
              width={bodyW}
              height={barH}
              fill={color}
              opacity="0.8"
            />
          </g>
        );
      })}
      <path d={pathOf(ma(5))} fill="none" stroke="#7c5cff" strokeWidth="1.2" />
      <path d={pathOf(ma(10))} fill="none" stroke="#2f6bff" strokeWidth="1.2" />
      <path d={pathOf(ma(20))} fill="none" stroke="#e08a2c" strokeWidth="1.2" />
      <text x={pad.l - 6} y={pad.t + 4} textAnchor="end" className="tick-axis">
        {max.toFixed(2)}
      </text>
      <text x={pad.l - 6} y={pad.t + plotH} textAnchor="end" className="tick-axis">
        {min.toFixed(2)}
      </text>
      <text x={pad.l} y={candleH - 6} className="tick-axis">
        {String(first.time).slice(0, 10)}
      </text>
      <text x={w - pad.r} y={candleH - 6} textAnchor="end" className="tick-axis">
        {String(last.time).slice(0, 10)}
      </text>
    </svg>
  );
}

/** Map TDX minute points → TickFlow MinuteKlineRow shape for EChartsIntraday. */
function toMinuteRows(
  points: Array<{ time: string; price: number; avg: number; volume: number }>,
  date: string,
): MinuteKlineRow[] {
  const day = date.slice(0, 10);
  return points.map((p, i) => {
    const prev = i > 0 ? points[i - 1].price : p.price;
    const close = p.price;
    const high = Math.max(prev, close);
    const low = Math.min(prev, close);
    const time = normalizeTime(p.time);
    const volume = Number(p.volume) || 0;
    const amount = p.avg > 0 && volume > 0 ? p.avg * volume * 100 : close * volume * 100;
    return {
      datetime: `${day} ${time}:00`,
      open: prev,
      high,
      low,
      close,
      volume,
      amount,
    };
  });
}

function normalizeTime(time: string): string {
  const m = String(time).match(/(\d{1,2}):(\d{2})/);
  if (!m) return "09:30";
  return `${String(Number(m[1])).padStart(2, "0")}:${m[2]}`;
}

function priceLimitForCode(code: string): PriceLimitInfo {
  const c = code.replace(/\D/g, "").padStart(6, "0").slice(-6);
  let rate = 0.1;
  if (c.startsWith("30") || c.startsWith("68")) rate = 0.2;
  else if (c.startsWith("8") || c.startsWith("4")) rate = 0.3;
  return { rate, limit_up: null, limit_down: null, source: "rule" };
}

function marketSuffix(code: string) {
  const c = code.replace(/\D/g, "").padStart(6, "0").slice(-6);
  if (c.startsWith("6") || c.startsWith("9")) return "SH";
  if (c.startsWith("8") || c.startsWith("4")) return "BJ";
  return "SZ";
}

function toneClass(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n) || n === 0) return "flat";
  return n > 0 ? "up" : "dn";
}

function fmtSigned(n: number | null) {
  if (n == null || !Number.isFinite(n)) return "--";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}`;
}

function fmtPct(n: number | null) {
  if (n == null || !Number.isFinite(n)) return "--";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export function stockFromRow(row: unknown[]): StockPick {
  return { code: String(row[0] || ""), name: String(row[1] || "") };
}
