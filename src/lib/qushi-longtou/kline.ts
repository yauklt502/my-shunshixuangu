const KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get";

const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
  Referer: "https://quote.eastmoney.com/",
  Accept: "application/json,text/plain,*/*",
};

type CacheEntry = { closes: number[]; exp: number };
const cache = new Map<string, CacheEntry>();

export function movingAverage(values: number[], period: number): number | null {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  const sum = slice.reduce((acc, value) => acc + value, 0);
  return sum / period;
}

export async function fetchRecentCloses(
  market: number,
  code: string,
  limit = 12,
): Promise<number[]> {
  const key = `${market}.${code}`;
  const hit = cache.get(key);
  if (hit && hit.exp > Date.now()) return hit.closes;

  const params = new URLSearchParams({
    secid: key,
    klt: "101",
    fqt: "1",
    lmt: String(limit),
    end: "20500101",
    fields1: "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
    fields2: "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
  });

  try {
    const response = await fetch(`${KLINE}?${params.toString()}`, {
      headers: HEADERS,
      cache: "no-store",
      signal: AbortSignal.timeout(6000),
    });
    if (!response.ok) return hit?.closes ?? [];
    const json = (await response.json()) as { data?: { klines?: string[] } };
    const closes: number[] = [];
    for (const row of json.data?.klines ?? []) {
      const close = Number(String(row).split(",")[2]);
      if (Number.isFinite(close)) closes.push(close);
    }
    cache.set(key, { closes, exp: Date.now() + 60_000 });
    return closes;
  } catch {
    return hit?.closes ?? [];
  }
}

export async function fetchClosesMany(
  items: { market: number; code: string }[],
): Promise<Map<string, number[]>> {
  const unique = new Map<string, { market: number; code: string }>();
  for (const item of items) {
    unique.set(`${item.market}.${item.code}`, item);
  }
  const entries = await Promise.all(
    [...unique.values()].map(async (item) => {
      const closes = await fetchRecentCloses(item.market, item.code);
      return [`${item.market}.${item.code}`, closes] as const;
    }),
  );
  return new Map(entries);
}
