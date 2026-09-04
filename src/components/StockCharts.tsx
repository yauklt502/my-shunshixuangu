import { useEffect, useMemo, useState } from "react";
import { Modal, Tabs } from "@/components/ui";
import { tdxKline, tdxMinute, toTdxCode } from "@/api/tdx";

type StockPick = { code: string; name: string };

export function StockChartModal({
  stock,
  date,
  onClose,
}: {
  stock: StockPick;
  date: string;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"minute" | "day">("minute");
  const tdxCode = toTdxCode(stock.code);

  return (
    <Modal title={`${stock.name}  ${stock.code}`} onClose={onClose}>
      <div className="card-bd chart-modal">
        <Tabs
          value={tab}
          onChange={(id) => setTab(id as "minute" | "day")}
          items={[
            { id: "minute", label: "分时" },
            { id: "day", label: "日K" },
          ]}
        />
        {tab === "minute" ? <MinutePane code={tdxCode} date={date} /> : <DayPane code={tdxCode} />}
        <div className="faint tip" style={{ marginTop: 10 }}>
          行情来自通达信主站（eltdx / tdx-mcp），与开盘啦竞价列表互补。
        </div>
      </div>
    </Modal>
  );
}

function MinutePane({ code, date }: { code: string; date: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [points, setPoints] = useState<Array<{ time: string; price: number; avg: number; volume: number }>>([]);
  const [prevClose, setPrevClose] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    const ymd = date.replaceAll("-", "");
    tdxMinute(code)
      .catch(() => tdxMinute(code, ymd))
      .then((data) => {
        if (!alive) return;
        setPoints(data.points || []);
        setPrevClose(data.prev_close ?? null);
      })
      .catch((err: Error) => {
        if (!alive) return;
        setError(err.message || "分时加载失败");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [code, date]);

  if (loading) return <div className="spinner">正在拉取分时…</div>;
  if (error) return <div className="error-box">{error}</div>;
  if (!points.length) return <div className="empty">暂无分时</div>;
  return <MinuteChart points={points} prevClose={prevClose} />;
}

function DayPane({ code }: { code: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bars, setBars] = useState<Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>>([]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    tdxKline(code, "day", 120)
      .then((data) => {
        if (!alive) return;
        setBars(data.bars || []);
      })
      .catch((err: Error) => {
        if (!alive) return;
        setError(err.message || "日K加载失败");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [code]);

  if (loading) return <div className="spinner">正在拉取日K…</div>;
  if (error) return <div className="error-box">{error}</div>;
  if (!bars.length) return <div className="empty">暂无日K</div>;
  return <CandleChart bars={bars} />;
}

function MinuteChart({
  points,
  prevClose,
}: {
  points: Array<{ time: string; price: number; avg: number; volume: number }>;
  prevClose: number | null;
}) {
  const w = 720;
  const h = 280;
  const pad = { l: 48, r: 16, t: 16, b: 28 };
  const prices = points.map((p) => p.price);
  const avgs = points.map((p) => p.avg).filter((n) => Number.isFinite(n));
  const base = prevClose && prevClose > 0 ? prevClose : prices[0];
  const min = Math.min(...prices, ...avgs, base) * 0.998;
  const max = Math.max(...prices, ...avgs, base) * 1.002;
  const span = Math.max(max - min, 0.01);
  const plotW = w - pad.l - pad.r;
  const plotH = h - pad.t - pad.b;
  const xAt = (i: number) => pad.l + (i / Math.max(points.length - 1, 1)) * plotW;
  const yAt = (v: number) => pad.t + ((max - v) / span) * plotH;
  const pricePath = points.map((p, i) => `${i ? "L" : "M"}${xAt(i).toFixed(1)},${yAt(p.price).toFixed(1)}`).join(" ");
  const avgPath = points.map((p, i) => `${i ? "L" : "M"}${xAt(i).toFixed(1)},${yAt(p.avg).toFixed(1)}`).join(" ");
  const last = points[points.length - 1];
  const tone = last.price >= base ? "up" : "dn";
  const midY = yAt(base);

  return (
    <div>
      <div className="chart-meta">
        <b className={tone}>{last.price.toFixed(2)}</b>
        <span className={tone}>{(((last.price - base) / base) * 100).toFixed(2)}%</span>
        <span className="faint">{last.time}</span>
      </div>
      <svg className="stock-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="分时图">
        <line x1={pad.l} y1={midY} x2={w - pad.r} y2={midY} stroke="rgba(15,23,42,0.12)" strokeDasharray="4 4" />
        <path d={pricePath} fill="none" stroke={last.price >= base ? "#e53935" : "#1aa37a"} strokeWidth="1.8" />
        <path d={avgPath} fill="none" stroke="#c48a12" strokeWidth="1.2" opacity="0.9" />
        <text x={pad.l - 6} y={pad.t + 4} textAnchor="end" fontSize="10" fill="#8a97a6">
          {max.toFixed(2)}
        </text>
        <text x={pad.l - 6} y={h - pad.b} textAnchor="end" fontSize="10" fill="#8a97a6">
          {min.toFixed(2)}
        </text>
        <text x={pad.l} y={h - 8} fontSize="10" fill="#8a97a6">
          {points[0]?.time}
        </text>
        <text x={w - pad.r} y={h - 8} textAnchor="end" fontSize="10" fill="#8a97a6">
          {last.time}
        </text>
      </svg>
    </div>
  );
}

function CandleChart({
  bars,
}: {
  bars: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>;
}) {
  const visible = useMemo(() => bars.slice(-90), [bars]);
  const w = 720;
  const h = 300;
  const pad = { l: 48, r: 16, t: 16, b: 36 };
  const highs = visible.map((b) => b.high);
  const lows = visible.map((b) => b.low);
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const span = Math.max(max - min, 0.01);
  const plotW = w - pad.l - pad.r;
  const plotH = h - pad.t - pad.b;
  const gap = plotW / visible.length;
  const bodyW = Math.max(2, gap * 0.62);
  const yAt = (v: number) => pad.t + ((max - v) / span) * plotH;
  const last = visible[visible.length - 1];
  const first = visible[0];
  const chg = first ? ((last.close - first.open) / first.open) * 100 : 0;

  return (
    <div>
      <div className="chart-meta">
        <b className={last.close >= last.open ? "up" : "dn"}>{last.close.toFixed(2)}</b>
        <span className={chg >= 0 ? "up" : "dn"}>{chg.toFixed(2)}%</span>
        <span className="faint">{String(last.time).slice(0, 10)} · {visible.length}根</span>
      </div>
      <svg className="stock-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="日K线">
        {visible.map((bar, i) => {
          const x = pad.l + i * gap + gap / 2;
          const up = bar.close >= bar.open;
          const color = up ? "#e53935" : "#1aa37a";
          const yHigh = yAt(bar.high);
          const yLow = yAt(bar.low);
          const yOpen = yAt(bar.open);
          const yClose = yAt(bar.close);
          const top = Math.min(yOpen, yClose);
          const bodyH = Math.max(1, Math.abs(yClose - yOpen));
          return (
            <g key={`${bar.time}-${i}`}>
              <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={color} strokeWidth="1" />
              <rect x={x - bodyW / 2} y={top} width={bodyW} height={bodyH} fill={color} />
            </g>
          );
        })}
        <text x={pad.l - 6} y={pad.t + 4} textAnchor="end" fontSize="10" fill="#8a97a6">
          {max.toFixed(2)}
        </text>
        <text x={pad.l - 6} y={h - pad.b} textAnchor="end" fontSize="10" fill="#8a97a6">
          {min.toFixed(2)}
        </text>
        <text x={pad.l} y={h - 10} fontSize="10" fill="#8a97a6">
          {String(first.time).slice(0, 10)}
        </text>
        <text x={w - pad.r} y={h - 10} textAnchor="end" fontSize="10" fill="#8a97a6">
          {String(last.time).slice(0, 10)}
        </text>
      </svg>
    </div>
  );
}

export function stockFromRow(row: unknown[]): StockPick {
  return { code: String(row[0] || ""), name: String(row[1] || "") };
}
