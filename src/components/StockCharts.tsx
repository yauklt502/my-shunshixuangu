import { useEffect, useId, useMemo, useState } from "react";
import { tdxKline, tdxMinute, toTdxCode } from "@/api/tdx";

type StockPick = { code: string; name: string };
type MinutePoint = { time: string; price: number; avg: number; volume: number };
type DayBar = { time: string; open: number; high: number; low: number; close: number; volume: number };
type ScaleMode = "auto" | "limit";

const SESSION_MARKS = [
  { label: "9:30", slot: 0 },
  { label: "10:30", slot: 60 },
  { label: "11:30/13:00", slot: 120 },
  { label: "14:00", slot: 180 },
  { label: "15:00", slot: 240 },
];
const SESSION_SLOTS = 241;

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
  const [scaleMode, setScaleMode] = useState<ScaleMode>("auto");
  const [minute, setMinute] = useState<{
    loading: boolean;
    error: string | null;
    points: MinutePoint[];
    prevClose: number | null;
  }>({ loading: true, error: null, points: [], prevClose: null });
  const [day, setDay] = useState<{
    loading: boolean;
    error: string | null;
    bars: DayBar[];
  }>({ loading: true, error: null, bars: [] });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    let alive = true;
    setMinute({ loading: true, error: null, points: [], prevClose: null });
    const ymd = date.replaceAll("-", "");
    tdxMinute(tdxCode)
      .catch(() => tdxMinute(tdxCode, ymd))
      .then((data) => {
        if (!alive) return;
        setMinute({
          loading: false,
          error: null,
          points: data.points || [],
          prevClose: data.prev_close ?? null,
        });
      })
      .catch((err: Error) => {
        if (!alive) return;
        setMinute({ loading: false, error: err.message || "分时加载失败", points: [], prevClose: null });
      });
    return () => {
      alive = false;
    };
  }, [tdxCode, date]);

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
    const lastMin = minute.points[minute.points.length - 1];
    const prev =
      minute.prevClose && minute.prevClose > 0
        ? minute.prevClose
        : day.bars.length > 1
          ? day.bars[day.bars.length - 2]?.close
          : lastBar?.open;
    const price = lastMin?.price ?? lastBar?.close ?? null;
    if (price == null || !prev || prev <= 0) {
      return { price: null as number | null, chg: null as number | null, pct: null as number | null };
    }
    const chg = price - prev;
    return { price, chg, pct: (chg / prev) * 100 };
  }, [day.bars, minute.points, minute.prevClose]);

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
          <div className="tick-stage-tabs" aria-hidden="true">
            {["成交量", "MACD", "RSI", "KDJ", "BOLL", "WR", "BIAS"].map((label) => (
              <span key={label} className={label === "成交量" ? "on" : undefined}>
                {label}
              </span>
            ))}
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

      <aside className="tick-panel" aria-label="分时浮窗">
        <button type="button" className="tick-close" onClick={onClose} aria-label="关闭浮窗">
          ×
        </button>
        <div className="tick-panel-hd">
          <div className="tick-panel-modes">
            <button
              type="button"
              className={scaleMode === "auto" ? "tick-mode on" : "tick-mode"}
              onClick={() => setScaleMode("auto")}
            >
              自适应
            </button>
            <button
              type="button"
              className={scaleMode === "limit" ? "tick-mode on" : "tick-mode"}
              onClick={() => setScaleMode("limit")}
            >
              涨跌停
            </button>
          </div>
          <div className="tick-panel-handle" />
        </div>
        <div className="tick-panel-bd">
          {minute.loading ? (
            <div className="spinner">正在拉取分时…</div>
          ) : minute.error ? (
            <div className="error-box">{minute.error}</div>
          ) : minute.points.length ? (
            <TickMinuteChart points={minute.points} prevClose={minute.prevClose} scaleMode={scaleMode} code={stock.code} />
          ) : (
            <div className="empty">暂无分时</div>
          )}
        </div>
      </aside>
    </div>
  );
}

function TickMinuteChart({
  points,
  prevClose,
  scaleMode,
  code,
}: {
  points: MinutePoint[];
  prevClose: number | null;
  scaleMode: ScaleMode;
  code: string;
}) {
  const fillId = `tickFill-${useId().replace(/:/g, "")}`;
  const w = 360;
  const priceH = 420;
  const volH = 108;
  const gap = 10;
  const totalH = priceH + gap + volH;
  const pad = { l: 44, r: 52, t: 12, b: 22 };

  const series = useMemo(() => alignSession(points), [points]);
  const prices = series.map((p) => p.price).filter((n): n is number => n != null && Number.isFinite(n));
  const base = prevClose && prevClose > 0 ? prevClose : prices[0] || 1;
  const limitPct = limitPercent(code);

  let maxAbsPct: number;
  if (scaleMode === "limit") {
    maxAbsPct = limitPct;
  } else {
    const extremes = prices.length ? prices : [base];
    const hi = Math.max(...extremes);
    const lo = Math.min(...extremes);
    maxAbsPct = Math.max(Math.abs((hi - base) / base), Math.abs((lo - base) / base), 0.01) * 100;
    maxAbsPct = Math.ceil(maxAbsPct * 100) / 100;
  }

  const maxPrice = base * (1 + maxAbsPct / 100);
  const minPrice = base * (1 - maxAbsPct / 100);
  const span = Math.max(maxPrice - minPrice, 0.01);
  const plotW = w - pad.l - pad.r;
  const plotH = priceH - pad.t - pad.b;
  const xAt = (slot: number) => pad.l + (slot / (SESSION_SLOTS - 1)) * plotW;
  const yAt = (price: number) => pad.t + ((maxPrice - price) / span) * plotH;
  const midY = yAt(base);

  const drawn = series.filter((p) => p.price != null);
  const pricePath = drawn
    .map((p, i) => `${i ? "L" : "M"}${xAt(p.slot).toFixed(1)},${yAt(p.price!).toFixed(1)}`)
    .join(" ");
  const areaPath =
    drawn.length > 1
      ? `${pricePath} L${xAt(drawn[drawn.length - 1].slot).toFixed(1)},${(pad.t + plotH).toFixed(1)} L${xAt(drawn[0].slot).toFixed(1)},${(pad.t + plotH).toFixed(1)} Z`
      : "";

  const last = drawn[drawn.length - 1];
  const lineUp = (last?.price ?? base) >= base;
  const lineColor = lineUp ? "#e53935" : "#1aa37a";
  const maxVol = Math.max(...series.map((p) => p.volume || 0), 1);
  const volTop = priceH + gap;
  const volPlotH = volH - 8;
  const cursorX = last ? xAt(last.slot) : null;

  return (
    <svg className="tick-chart" viewBox={`0 0 ${w} ${totalH}`} role="img" aria-label="分时图">
      <defs>
        <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={lineColor} stopOpacity="0.28" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {SESSION_MARKS.map((mark) => (
        <line
          key={`g-${mark.slot}`}
          x1={xAt(mark.slot)}
          y1={pad.t}
          x2={xAt(mark.slot)}
          y2={pad.t + plotH}
          stroke="rgba(15,23,42,0.08)"
          strokeWidth="1"
        />
      ))}
      <line
        x1={pad.l}
        y1={midY}
        x2={w - pad.r}
        y2={midY}
        stroke="rgba(15,23,42,0.28)"
        strokeDasharray="4 3"
        strokeWidth="1"
      />

      {areaPath ? <path d={areaPath} fill={`url(#${fillId})`} /> : null}
      {pricePath ? <path d={pricePath} fill="none" stroke={lineColor} strokeWidth="1.6" /> : null}

      {cursorX != null ? (
        <line
          x1={cursorX}
          y1={pad.t}
          x2={cursorX}
          y2={pad.t + plotH}
          stroke="rgba(15,23,42,0.22)"
          strokeDasharray="3 3"
          strokeWidth="1"
        />
      ) : null}

      <text x={pad.l - 6} y={pad.t + 10} textAnchor="end" className="tick-axis">
        {maxPrice.toFixed(2)}
      </text>
      <text x={pad.l - 6} y={midY + 3} textAnchor="end" className="tick-axis">
        {base.toFixed(2)}
      </text>
      <text x={pad.l - 6} y={pad.t + plotH} textAnchor="end" className="tick-axis">
        {minPrice.toFixed(2)}
      </text>

      <text x={w - pad.r + 6} y={pad.t + 10} className="tick-axis up">
        +{maxAbsPct.toFixed(2)}%
      </text>
      <text x={w - pad.r + 6} y={midY + 3} className="tick-axis">
        0.00%
      </text>
      <text x={w - pad.r + 6} y={pad.t + plotH} className="tick-axis dn">
        -{maxAbsPct.toFixed(2)}%
      </text>

      {SESSION_MARKS.map((mark) => (
        <text
          key={`t-${mark.slot}`}
          x={xAt(mark.slot)}
          y={priceH - 4}
          textAnchor={mark.slot === 0 ? "start" : mark.slot === SESSION_SLOTS - 1 ? "end" : "middle"}
          className="tick-axis"
        >
          {mark.label}
        </text>
      ))}

      {series.map((p, i) => {
        if (!p.volume || p.price == null) return null;
        const prev = i > 0 ? series[i - 1].price : base;
        const up = p.price >= (prev ?? base);
        const barH = Math.max(1, (p.volume / maxVol) * volPlotH);
        const bx = xAt(p.slot);
        const bw = Math.max(1.2, plotW / SESSION_SLOTS - 0.4);
        return (
          <rect
            key={`v-${p.slot}`}
            x={bx - bw / 2}
            y={volTop + (volPlotH - barH)}
            width={bw}
            height={barH}
            fill={up ? "#e53935" : "#1aa37a"}
            opacity="0.85"
          />
        );
      })}
    </svg>
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
  const ma5 = ma(5);
  const ma10 = ma(10);
  const ma20 = ma(20);
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
      <path d={pathOf(ma5)} fill="none" stroke="#7c5cff" strokeWidth="1.2" />
      <path d={pathOf(ma10)} fill="none" stroke="#2f6bff" strokeWidth="1.2" />
      <path d={pathOf(ma20)} fill="none" stroke="#e08a2c" strokeWidth="1.2" />
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

function alignSession(points: MinutePoint[]) {
  const bySlot = new Map<number, MinutePoint>();
  for (const p of points) {
    const slot = timeToSlot(p.time);
    if (slot == null) continue;
    bySlot.set(slot, p);
  }
  const out: Array<{ slot: number; price: number | null; volume: number; time: string }> = [];
  for (let slot = 0; slot < SESSION_SLOTS; slot++) {
    const hit = bySlot.get(slot);
    out.push({
      slot,
      price: hit ? hit.price : null,
      volume: hit?.volume || 0,
      time: hit?.time || "",
    });
  }
  // If slot mapping failed for all, fall back to sequential plot within morning+afternoon length
  if (!out.some((p) => p.price != null) && points.length) {
    return points.slice(0, SESSION_SLOTS).map((p, i) => ({
      slot: i,
      price: p.price,
      volume: p.volume,
      time: p.time,
    }));
  }
  return out;
}

function timeToSlot(time: string): number | null {
  const m = String(time).match(/(\d{1,2}):(\d{2})/);
  if (!m) return null;
  const hh = Number(m[1]);
  const mm = Number(m[2]);
  const mins = hh * 60 + mm;
  const amStart = 9 * 60 + 30;
  const amEnd = 11 * 60 + 30;
  const pmStart = 13 * 60;
  const pmEnd = 15 * 60;
  if (mins >= amStart && mins <= amEnd) return mins - amStart;
  if (mins >= pmStart && mins <= pmEnd) return 120 + (mins - pmStart);
  return null;
}

function limitPercent(code: string) {
  const c = code.replace(/\D/g, "").padStart(6, "0").slice(-6);
  if (c.startsWith("30") || c.startsWith("68")) return 20;
  if (c.startsWith("8") || c.startsWith("4")) return 30;
  return 10;
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
