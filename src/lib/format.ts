const YI = 1e8;
const WAN = 1e4;

export function asNumber(value: unknown): number | null {
  if (value === "-" || value === "" || value === null || value === undefined) {
    return null;
  }
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function asString(value: unknown): string | null {
  if (value === null || value === undefined || value === "-") return null;
  const s = String(value).trim();
  return s ? s : null;
}

export function formatAmount(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "--";
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= YI) return `${sign}${(abs / YI).toFixed(digits)}亿`;
  if (abs >= WAN) return `${sign}${(abs / WAN).toFixed(abs >= 10 * WAN ? 0 : 1)}万`;
  return `${sign}${abs.toFixed(0)}`;
}

export function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

export function formatPrice(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "--";
  return value.toFixed(digits);
}

export function formatFbt(value: number | null | undefined): string | null {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  const raw = Math.trunc(value);
  if (raw <= 0) return null;
  const s = String(raw).padStart(6, "0");
  return `${s.slice(0, 2)}:${s.slice(2, 4)}:${s.slice(4, 6)}`;
}

/** Convert `HH:MM` or `HH:MM:SS` (同花顺涨停时间) to eastmoney-style HHMMSS integer. */
export function parseHhMmToFbt(value: string | number | null | undefined): number {
  if (value == null || value === "") return 0;
  if (typeof value === "number" && Number.isFinite(value)) {
    const n = Math.trunc(value);
    if (n > 235959) return 0;
    if (n < 10000) return n * 100;
    return n;
  }
  const raw = String(value).trim();
  const match = raw.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) return 0;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  const second = Number(match[3] ?? 0);
  if (hour > 23 || minute > 59 || second > 59) return 0;
  return hour * 10000 + minute * 100 + second;
}

export function formatYmd(value: string | number | null | undefined): string {
  const raw = String(value ?? "").replaceAll("-", "");
  if (raw.length !== 8) return "--";
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
}

export function beijingYmd(date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
  return parts.replaceAll("-", "");
}

export function normalizeYmd(value: string | null | undefined): string | null {
  const raw = String(value ?? "").replaceAll("-", "").trim();
  if (!/^\d{8}$/.test(raw)) return null;
  return raw;
}

export function ymdToDateInput(ymd: string): string {
  const normalized = normalizeYmd(ymd);
  if (!normalized) return "";
  return `${normalized.slice(0, 4)}-${normalized.slice(4, 6)}-${normalized.slice(6, 8)}`;
}

export function dateInputToYmd(value: string): string | null {
  return normalizeYmd(value);
}

export function ymdToShanghaiMs(ymd: string): number {
  const normalized = normalizeYmd(ymd);
  if (!normalized) return Date.now();
  return new Date(
    `${normalized.slice(0, 4)}-${normalized.slice(4, 6)}-${normalized.slice(6, 8)}T00:00:00+08:00`,
  ).getTime();
}

export function isTodayYmd(ymd: string): boolean {
  const normalized = normalizeYmd(ymd);
  return normalized != null && normalized === beijingYmd();
}

export function beijingClock(date = new Date()): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).format(date);
}

export function signedClass(value: number | null | undefined): "up" | "down" | "flat" {
  if (value === null || value === undefined || value === 0 || !Number.isFinite(value)) {
    return "flat";
  }
  return value > 0 ? "up" : "down";
}

export function downsample(points: number[], size = 48): number[] {
  if (points.length <= size) return points;
  const out: number[] = [];
  const step = (points.length - 1) / (size - 1);
  for (let i = 0; i < size; i += 1) {
    out.push(points[Math.round(i * step)]!);
  }
  return out;
}

export function quoteUrl(market: number, code: string): string {
  return `https://quote.eastmoney.com/unify/r/${market}.${code}`;
}

export function boardUrl(code: string): string {
  return `https://quote.eastmoney.com/bk/${code}.html`;
}
