import { useMemo, useState, type ReactNode } from "react";
import { fmtPct, num, pctClass, str } from "@/lib/format";

export function Card({
  title,
  extra,
  children,
  className = "",
}: {
  title?: string;
  extra?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || extra) && (
        <div className="card-hd">
          {title ? <h3>{title}</h3> : <span />}
          {extra}
        </div>
      )}
      <div className="card-bd">{children}</div>
    </section>
  );
}

export function Kpi({
  label,
  value,
  meta,
  tone,
}: {
  label: string;
  value: ReactNode;
  meta?: ReactNode;
  tone?: "up" | "dn" | "flat";
}) {
  return (
    <div className="card kpi">
      <div className="label">{label}</div>
      <div className={`value ${tone || ""}`}>{value}</div>
      {meta ? <div className="meta">{meta}</div> : null}
    </div>
  );
}

export function Tabs({
  value,
  onChange,
  items,
}: {
  value: string;
  onChange: (value: string) => void;
  items: Array<{ id: string; label: string }>;
}) {
  return (
    <div className="tabs">
      {items.map((item) => (
        <button key={item.id} className={`tab ${value === item.id ? "active" : ""}`} onClick={() => onChange(item.id)}>
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function Spinner({ text = "正在拉取行情..." }: { text?: string }) {
  return <div className="spinner">{text}</div>;
}

export function Empty({ text = "暂无数据" }: { text?: string }) {
  return <div className="empty">{text}</div>;
}

export function ErrorBox({ text }: { text: string }) {
  return <div className="error-box">{text}</div>;
}

export function StateGate({
  loading,
  error,
  empty,
  children,
}: {
  loading: boolean;
  error: string | null;
  empty?: boolean;
  children: ReactNode;
}) {
  if (loading) return <Spinner />;
  if (error) return <ErrorBox text={error} />;
  if (empty) return <Empty />;
  return <>{children}</>;
}

export type Col<T> = {
  key: string;
  title: string;
  align?: "left" | "right";
  render?: (row: T, index: number) => ReactNode;
  className?: (row: T) => string;
  sortValue?: (row: T) => number | string;
};

type SortState = { key: string; dir: 1 | -1 };

function compareSortValues(a: number | string, b: number | string, dir: 1 | -1) {
  const aNum = typeof a === "number";
  const bNum = typeof b === "number";
  if (aNum && bNum) {
    const aOk = Number.isFinite(a);
    const bOk = Number.isFinite(b);
    if (!aOk && !bOk) return 0;
    if (!aOk) return 1;
    if (!bOk) return -1;
    return (a - b) * dir;
  }
  return String(a).localeCompare(String(b), "zh-CN") * dir;
}

export function Table<T>({
  columns,
  rows,
  onRowClick,
  rowKey,
  loading,
  error,
  emptyText = "暂无数据",
}: {
  columns: Array<Col<T>>;
  rows: T[];
  onRowClick?: (row: T) => void;
  rowKey?: (row: T, index: number) => string;
  loading?: boolean;
  error?: string | null;
  emptyText?: string;
}) {
  const [sort, setSort] = useState<SortState | null>(null);

  const sortedRows = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((item) => item.key === sort.key);
    if (!col?.sortValue) return rows;
    const copy = rows.slice();
    copy.sort((left, right) => compareSortValues(col.sortValue!(left), col.sortValue!(right), sort.dir));
    return copy;
  }, [columns, rows, sort]);

  const toggleSort = (col: Col<T>) => {
    if (!col.sortValue) return;
    setSort((prev) => {
      if (prev?.key !== col.key) return { key: col.key, dir: -1 };
      if (prev.dir === -1) return { key: col.key, dir: 1 };
      return null;
    });
  };

  const status = loading ? "正在拉取行情..." : error || (sortedRows.length ? null : emptyText);

  return (
    <div className="tbl-wrap">
      <table className="data">
        <thead>
          <tr>
            {columns.map((col) => {
              const active = sort?.key === col.key;
              const classes = [
                col.align === "right" ? "right" : "",
                col.sortValue ? "sortable" : "",
                active ? "sorted" : "",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <th
                  key={col.key}
                  className={classes}
                  onClick={() => toggleSort(col)}
                  title={col.sortValue ? "点击排序" : undefined}
                  aria-sort={active ? (sort?.dir === -1 ? "descending" : "ascending") : undefined}
                >
                  {col.title}
                  {col.sortValue ? (
                    <span className="sort-mark">{active ? (sort?.dir === -1 ? "▼" : "▲") : "↕"}</span>
                  ) : null}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {status ? (
            <tr>
              <td className={`empty-cell ${error ? "error-box" : ""}`} colSpan={columns.length}>
                {status}
              </td>
            </tr>
          ) : (
            sortedRows.map((row, index) => (
              <tr
                key={rowKey ? `${rowKey(row, index)}-${index}` : index}
                className={onRowClick ? "click" : ""}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col) => (
                  <td key={col.key} className={`${col.align === "right" ? "right" : ""} ${col.className?.(row) || ""}`}>
                    {col.render ? col.render(row, index) : String((row as Record<string, unknown>)[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function StockCell({ code, name }: { code: unknown; name: unknown }) {
  return (
    <div className="stock">
      <b>{str(name)}</b>
      <span>{str(code)}</span>
    </div>
  );
}

export function Pct({ value }: { value: unknown }) {
  const n = typeof value === "string" && value.includes("%") ? Number(value.replace("%", "")) : num(value);
  return <span className={pctClass(n)}>{fmtPct(n)}</span>;
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="关闭">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function SentimentGauge({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  const angle = -120 + (clamped / 100) * 240;
  const tone = clamped >= 75 ? "up" : clamped <= 25 ? "dn" : "flat";
  return (
    <svg viewBox="0 0 180 130" width="180" height="130">
      <path d="M20 110 A70 70 0 1 1 160 110" fill="none" stroke="rgba(15,23,42,0.08)" strokeWidth="12" strokeLinecap="round" />
      <path
        d="M20 110 A70 70 0 1 1 160 110"
        fill="none"
        stroke="url(#g)"
        strokeWidth="12"
        strokeLinecap="round"
        strokeDasharray={`${(clamped / 100) * 220} 220`}
      />
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#27c79a" />
          <stop offset="50%" stopColor="#e8c36a" />
          <stop offset="100%" stopColor="#ff5d61" />
        </linearGradient>
      </defs>
      <g transform={`rotate(${angle} 90 110)`}>
        <line x1="90" y1="110" x2="90" y2="48" stroke="#1a2332" strokeWidth="2" />
        <circle cx="90" cy="110" r="4" fill="#e8c36a" />
      </g>
      <text x="90" y="96" textAnchor="middle" fill="currentColor" className={tone} fontSize="22" fontFamily="IBM Plex Mono">
        {clamped}
      </text>
      <text x="22" y="126" fill="#8a97a6" fontSize="10">
        冰点
      </text>
      <text x="150" y="126" fill="#8a97a6" fontSize="10">
        过热
      </text>
    </svg>
  );
}

export function VolumeChart({ trends }: { trends?: Array<Array<string>> }) {
  if (!trends?.length) return <Empty text="暂无分时量能" />;
  const values = trends.map((row) => Number(row[1]) || 0);
  const compare = trends.map((row) => Number(row[2]) || 0);
  const max = Math.max(...values, ...compare, 1);
  const w = 560;
  const h = 150;
  const step = w / Math.max(values.length - 1, 1);
  const toPath = (series: number[]) =>
    series
      .map((v, i) => {
        const x = i * step;
        const y = h - 12 - (v / max) * (h - 24);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <path d={toPath(compare)} fill="none" stroke="rgba(110,168,255,0.45)" strokeWidth="1.5" />
      <path d={toPath(values)} fill="none" stroke="#c48a12" strokeWidth="2" />
    </svg>
  );
}

export function BoardLadder({ counts }: { counts: number[] }) {
  const labels = ["一板", "二板", "三板", "四板", "五板+"];
  const max = Math.max(...counts, 1);
  return (
    <div className="ladder">
      {labels.map((label, i) => (
        <div className="ladder-row" key={label}>
          <span>{label}</span>
          <div className="bar">
            <i style={{ width: `${((counts[i] || 0) / max) * 100}%` }} />
          </div>
          <b className="mono">{counts[i] || 0}</b>
        </div>
      ))}
    </div>
  );
}
