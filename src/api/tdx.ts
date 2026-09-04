export async function tdxKline(code: string, period = "day", count = 120) {
  const qs = new URLSearchParams({ code, period, count: String(count) });
  const res = await fetch(`/api/tdx/kline?${qs}`);
  const data = await res.json();
  if (!res.ok || String(data.errcode) !== "0") throw new Error(data.errmsg || "日K获取失败");
  return data as {
    code: string;
    exchange: string;
    period: string;
    bars: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number; amount: number; last_close?: number | null }>;
  };
}

export async function tdxMinute(code: string, date = "") {
  const qs = new URLSearchParams({ code });
  if (date) qs.set("date", date);
  const res = await fetch(`/api/tdx/minute?${qs}`);
  const data = await res.json();
  if (!res.ok || String(data.errcode) !== "0") throw new Error(data.errmsg || "分时获取失败");
  return data as {
    code: string;
    exchange: string;
    trading_date?: string | null;
    prev_close?: number | null;
    points: Array<{ time: string; price: number; avg: number; volume: number }>;
  };
}

export function toTdxCode(raw: unknown): string {
  const text = String(raw || "").trim().toLowerCase();
  if (!text) return "";
  if (/^(sh|sz|bj)\d{6}$/.test(text)) return text;
  const code = text.replace(/^(sh|sz|bj)/, "").replace(/\D/g, "").slice(-6);
  if (code.length !== 6) return text;
  if (code.startsWith("6") || code.startsWith("5") || code.startsWith("9")) return `sh${code}`;
  if (code.startsWith("8") || code.startsWith("4")) return `bj${code}`;
  return `sz${code}`;
}
