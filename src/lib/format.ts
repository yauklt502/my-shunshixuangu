export const TZ = "Asia/Shanghai";

export function chinaDate(d = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}

export function compactDate(iso: string): string {
  return iso.replaceAll("-", "");
}

export function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + days));
  return dt.toISOString().slice(0, 10);
}

export function weekday(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).getUTCDay();
}

export function isWeekend(iso: string): boolean {
  const day = weekday(iso);
  return day === 0 || day === 6;
}

export function shiftTradingDay(iso: string, dir: -1 | 1, holidays: Set<string>): string {
  let cursor = iso;
  for (let i = 0; i < 16; i += 1) {
    cursor = addDays(cursor, dir);
    if (!isWeekend(cursor) && !holidays.has(cursor)) return cursor;
  }
  return cursor;
}

export function lastTradingDay(iso: string, holidays: Set<string>): string {
  if (!isWeekend(iso) && !holidays.has(iso)) return iso;
  return shiftTradingDay(iso, -1, holidays);
}

/** 当前应展示的行情日：开盘前（09:15 前）仍用上一交易日。 */
export function marketSessionDate(holidays: Set<string>, now = new Date()): string {
  const cal = chinaDate(now);
  if (chinaMinutes(now) < 9 * 60 + 15) {
    return shiftTradingDay(cal, -1, holidays);
  }
  return lastTradingDay(cal, holidays);
}

export function formatClock(d = new Date()): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(d);
}

export function formatHm(tsSec: number | string | undefined | null): string {
  const n = Number(tsSec);
  if (!Number.isFinite(n) || n <= 0) return "--";
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(n * 1000));
}

export const fmtHm = formatHm;

export function formatDateTime(tsSec: number | string | undefined | null): string {
  const n = Number(tsSec);
  if (!Number.isFinite(n) || n <= 0) return "--";
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: TZ,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(n * 1000));
}

export const fmtDateTime = formatDateTime;

export function chinaMinutes(d = new Date()): number {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(d);
  const hour = Number(parts.find((p) => p.type === "hour")?.value || 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value || 0);
  return hour * 60 + minute;
}

export function isMarketHours(d = new Date()): boolean {
  const mins = chinaMinutes(d);
  return mins >= 9 * 60 + 15 && mins <= 15 * 60 + 5;
}

export function num(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const cleaned = value.replace(/[%,\s]/g, "");
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : fallback;
  }
  return fallback;
}

export function fmtMoney(value: unknown, empty = "--"): string {
  const n = num(value, NaN);
  if (!Number.isFinite(n)) return empty;
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1e8) return `${sign}${(abs / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `${sign}${(abs / 1e4).toFixed(abs >= 1e6 ? 0 : 1)}万`;
  return `${sign}${abs.toFixed(0)}`;
}

export function fmtYi(value: unknown, empty = "--"): string {
  const n = num(value, NaN);
  if (!Number.isFinite(n)) return empty;
  return `${(n / 1e8).toFixed(2)}亿`;
}

export function fmtPct(value: unknown, digits = 2): string {
  const n = num(value, NaN);
  if (!Number.isFinite(n)) return "--";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

export function pctClass(value: unknown): string {
  const n = num(value, 0);
  if (n > 0) return "up";
  if (n < 0) return "dn";
  return "flat";
}

export function parsePct(value: unknown): number {
  if (typeof value === "number") return value;
  if (typeof value === "string") return num(value.replace("%", ""));
  return 0;
}

export function deviceId(): string {
  const key = "kpl.deviceId";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const id = crypto.randomUUID().replaceAll("-", "");
  localStorage.setItem(key, id);
  return id;
}

export function unwrapList(info: unknown): unknown[][] {
  if (!Array.isArray(info) || info.length === 0) return [];
  const first = info[0];
  if (Array.isArray(first) && Array.isArray(first[0])) return first as unknown[][];
  if (Array.isArray(first) && (typeof first[0] === "string" || typeof first[0] === "number")) {
    const last = info[info.length - 1];
    if (typeof last === "string" || typeof last === "number") {
      const maybeStocks = info.slice(0, -1);
      if (maybeStocks.every((row) => Array.isArray(row))) return maybeStocks as unknown[][];
    }
    return info.filter((row) => Array.isArray(row)) as unknown[][];
  }
  return [];
}

export function str(value: unknown, fallback = ""): string {
  if (value === undefined || value === null) return fallback;
  return String(value).trim();
}
