import { asNumber, asString, beijingYmd, downsample } from "./format";
import type {
  BoardKind,
  BoardQuote,
  IndexQuote,
  StockQuote,
  ZbInfo,
  ZtInfo,
} from "./types";

const PUSH2 = "https://push2delay.eastmoney.com/api/qt";
const PUSH2EX = "https://push2ex.eastmoney.com";
const UT = "bd1d9ddb04089700cf9c27f6f7426281";
const ZT_UT = "7eea3edcaed734bea9cbfc24409ed989";

const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
  Referer: "https://quote.eastmoney.com/center/boardlist.html",
  Accept: "application/json,text/plain,*/*",
};

type CacheEntry<T> = { value: T; exp: number };

const cache = new Map<string, CacheEntry<unknown>>();

async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = cache.get(key);
  if (hit && hit.exp > Date.now()) return hit.value as T;
  const value = await fn();
  cache.set(key, { value, exp: Date.now() + ttlMs });
  return value;
}

function diffRows(payload: unknown): Record<string, unknown>[] {
  const root = payload as { data?: { diff?: unknown } };
  const diff = root?.data?.diff;
  if (!diff) return [];
  if (Array.isArray(diff)) return diff as Record<string, unknown>[];
  return Object.values(diff as Record<string, Record<string, unknown>>);
}

async function fetchJson(url: string, timeoutMs = 8000): Promise<unknown> {
  const response = await fetch(url, {
    headers: HEADERS,
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) {
    throw new Error(`行情接口 ${response.status}: ${url}`);
  }
  return response.json();
}

function clistUrl(fs: string, fields: string, pz: number, fid = "f3"): string {
  const params = new URLSearchParams({
    pn: "1",
    pz: String(pz),
    po: "1",
    np: "1",
    ut: UT,
    fltt: "2",
    invt: "2",
    fid,
    fs,
    fields,
    _: String(Date.now()),
  });
  return `${PUSH2}/clist/get?${params.toString()}`;
}

export async function fetchIndices(): Promise<IndexQuote[]> {
  return cached("indices", 4000, async () => {
    const params = new URLSearchParams({
      fltt: "2",
      invt: "2",
      secids: "1.000001,0.399001,0.399006,1.000688",
      fields: "f12,f14,f2,f3,f4,f6,f104,f105,f106",
    });
    const json = await fetchJson(`${PUSH2}/ulist.np/get?${params.toString()}`);
    return diffRows(json).map((row) => ({
      code: asString(row.f12) ?? "",
      name: asString(row.f14) ?? "",
      price: asNumber(row.f2),
      changePercent: asNumber(row.f3),
      change: asNumber(row.f4),
      amount: asNumber(row.f6),
      upCount: asNumber(row.f104),
      downCount: asNumber(row.f105),
      flatCount: asNumber(row.f106),
    }));
  });
}

function parseBoard(row: Record<string, unknown>, kind: BoardKind): BoardQuote {
  return {
    code: asString(row.f12) ?? "",
    name: asString(row.f14) ?? "",
    kind,
    price: asNumber(row.f2),
    changePercent: asNumber(row.f3),
    amount: asNumber(row.f6),
    turnoverRate: asNumber(row.f8),
    mainNetInflow: asNumber(row.f62),
    mainNetInflowPercent: asNumber(row.f184),
    upCount: asNumber(row.f104),
    downCount: asNumber(row.f105),
    leadName: asString(row.f128),
    leadCode: asString(row.f140),
    leadChangePercent: asNumber(row.f136),
  };
}

export async function fetchBoards(kind: BoardKind): Promise<BoardQuote[]> {
  const fs = kind === "concept" ? "m:90+t:3+f:!50" : "m:90+t:2+f:!50";
  return cached(`boards:${kind}`, 4000, async () => {
    const json = await fetchJson(
      clistUrl(
        fs,
        "f12,f14,f2,f3,f6,f8,f62,f104,f105,f128,f136,f140,f184",
        80,
      ),
    );
    return diffRows(json)
      .map((row) => parseBoard(row, kind))
      .filter((board) => board.code && board.name);
  });
}

export async function fetchConstituents(boardCode: string): Promise<StockQuote[]> {
  return cached(`members:${boardCode}`, 4000, async () => {
    const json = await fetchJson(
      clistUrl(
        `b:${boardCode}+f:!50`,
        "f12,f13,f14,f2,f3,f6,f8,f15,f16,f17,f22,f62",
        80,
      ),
    );
    return diffRows(json)
      .map((row) => ({
        code: asString(row.f12) ?? "",
        name: asString(row.f14) ?? "",
        market: asNumber(row.f13) ?? 0,
        price: asNumber(row.f2),
        changePercent: asNumber(row.f3),
        amount: asNumber(row.f6),
        turnoverRate: asNumber(row.f8),
        high: asNumber(row.f15),
        low: asNumber(row.f16),
        open: asNumber(row.f17),
        speed: asNumber(row.f22),
        mainNetInflow: asNumber(row.f62),
      }))
      .filter((stock) => stock.code && stock.name);
  });
}

function parseZtItem(row: Record<string, unknown>): ZtInfo | null {
  const code = asString(row.c);
  if (!code) return null;
  const stat = (row.zttj ?? {}) as { days?: unknown; ct?: unknown };
  return {
    code,
    name: asString(row.n) ?? code,
    firstSealTime: asNumber(row.fbt) ?? 0,
    lastSealTime: asNumber(row.lbt) ?? 0,
    consecutiveBoards: asNumber(row.lbc) ?? 1,
    sealAmount: asNumber(row.fund),
    openCount: asNumber(row.zbc) ?? 0,
    ztDays: asNumber(stat.days) ?? 0,
    ztBoards: asNumber(stat.ct) ?? 0,
    industry: asString(row.hybk),
  };
}

function parseZbItem(row: Record<string, unknown>): ZbInfo | null {
  const code = asString(row.c);
  if (!code) return null;
  return {
    code,
    name: asString(row.n) ?? code,
    firstSealTime: asNumber(row.fbt) ?? 0,
    openCount: asNumber(row.zbc) ?? 1,
    changePercent: asNumber(row.zdp),
    industry: asString(row.hybk),
  };
}

export async function fetchZtPool(date = beijingYmd()): Promise<{
  qdate: string;
  tc: number;
  pool: ZtInfo[];
}> {
  return cached(`zt:${date}`, 8000, async () => {
    const params = new URLSearchParams({
      ut: ZT_UT,
      dpt: "wz.ztzt",
      Pageindex: "0",
      pagesize: "500",
      sort: "fbt:asc",
      date,
    });
    const json = (await fetchJson(`${PUSH2EX}/getTopicZTPool?${params.toString()}`)) as {
      data?: { qdate?: string | number; tc?: number; pool?: Record<string, unknown>[] };
    };
    const data = json.data ?? {};
    const pool = (data.pool ?? []).map(parseZtItem).filter((item): item is ZtInfo => Boolean(item));
    return {
      qdate: String(data.qdate ?? date),
      tc: data.tc ?? pool.length,
      pool,
    };
  });
}

export async function fetchZbPool(date = beijingYmd()): Promise<{
  qdate: string;
  tc: number;
  pool: ZbInfo[];
}> {
  return cached(`zb:${date}`, 8000, async () => {
    const params = new URLSearchParams({
      ut: ZT_UT,
      dpt: "wz.ztzt",
      Pageindex: "0",
      pagesize: "300",
      sort: "fbt:asc",
      date,
    });
    const json = (await fetchJson(`${PUSH2EX}/getTopicZBPool?${params.toString()}`)) as {
      data?: { qdate?: string | number; tc?: number; pool?: Record<string, unknown>[] };
    };
    const data = json.data ?? {};
    const pool = (data.pool ?? []).map(parseZbItem).filter((item): item is ZbInfo => Boolean(item));
    return {
      qdate: String(data.qdate ?? date),
      tc: data.tc ?? pool.length,
      pool,
    };
  });
}

export async function fetchTrend(secid: string): Promise<number[]> {
  return cached(`trend:${secid}`, 15000, async () => {
    const params = new URLSearchParams({
      secid,
      ndays: "1",
      iscr: "0",
      fields1: "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
      fields2: "f51,f52,f53,f54,f55,f56,f57,f58",
    });
    const json = (await fetchJson(`${PUSH2}/stock/trends2/get?${params.toString()}`)) as {
      data?: { trends?: string[] };
    };
    const rows = json.data?.trends ?? [];
    const prices: number[] = [];
    for (const row of rows) {
      const price = Number(String(row).split(",")[1]);
      if (Number.isFinite(price)) prices.push(price);
    }
    return downsample(prices, 60);
  });
}

export async function fetchTrendsMany(secids: string[]): Promise<Record<string, number[]>> {
  const unique = [...new Set(secids.filter(Boolean))];
  const entries = await Promise.all(
    unique.map(async (secid) => {
      try {
        return [secid, await fetchTrend(secid)] as const;
      } catch {
        return [secid, [] as number[]] as const;
      }
    }),
  );
  return Object.fromEntries(entries);
}
