import { asNumber, asString, parseHhMmToFbt } from "./format";
import { isNoiseBoard, isStStock } from "./noise-boards";
import { rankLeaders, rankMarketLeaders } from "./ranking";
import { getMarketSession } from "./market-hours";
import type {
  BoardKind,
  BoardQuote,
  IndexQuote,
  MarketSnapshot,
  SectorSnapshot,
  SectorSort,
  StockQuote,
  Universe,
  ZbInfo,
  ZtInfo,
} from "./types";

const FUYAO_BASE = "https://fuyao.aicubes.cn";
const SNAPSHOT_CHUNK = 250;
const STOCK_CHUNK = 120;

const INDEX_LIST: { thscode: string; name: string }[] = [
  { thscode: "000001.SH", name: "上证指数" },
  { thscode: "399001.SZ", name: "深证成指" },
  { thscode: "399006.SZ", name: "创业板指" },
  { thscode: "000688.SH", name: "科创50" },
];

type Envelope<T> = {
  code: number;
  message?: string;
  data?: T;
};

type CatalogItem = { thscode: string; name: string };
type PriceItem = {
  thscode?: string;
  ticker?: string;
  name?: string;
  last_price?: number;
  price_change?: number;
  price_change_ratio_pct?: number;
  volume?: number;
  turnover?: number;
  open_price?: number;
  high_price?: number;
  low_price?: number;
  prev_price?: number;
};

type LimitUpItem = {
  thscode?: string;
  ticker?: string;
  name?: string;
  is_st?: boolean;
  last_price?: number;
  price_change_ratio_pct?: number;
  limit_up_time?: string;
  continue_day_cnt?: number;
  seal_money?: number;
  max_seal_money?: number;
};

type LimitBreakItem = {
  thscode?: string;
  ticker?: string;
  name?: string;
  last_price?: number;
  price_change_ratio_pct?: number;
  open_times?: number;
  turnover_ratio_pct?: number;
  turnover?: number;
};

type PageData<T> = {
  timestamp?: number;
  pagination?: { total?: number; pages?: number; size?: number; page?: number };
  item?: T[];
};

type CacheEntry<T> = { value: T; exp: number };
const cache = new Map<string, CacheEntry<unknown>>();

async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = cache.get(key) as CacheEntry<T> | undefined;
  if (hit && hit.exp > Date.now()) return hit.value;
  const value = await fn();
  cache.set(key, { value, exp: Date.now() + ttlMs });
  return value;
}

export function chunkList<T>(items: T[], size: number): T[][] {
  if (size <= 0) return [items];
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

export function parseThsCode(thscode: string | null | undefined): {
  code: string;
  market: number;
  exchange: string;
} | null {
  if (!thscode) return null;
  const raw = thscode.trim().toUpperCase();
  const stock = raw.match(/^(\d{6})\.(SH|SZ|BJ)$/);
  if (stock) {
    return {
      code: stock[1]!,
      market: stock[2] === "SH" ? 1 : 0,
      exchange: stock[2]!,
    };
  }
  const other = raw.match(/^([0-9A-Z]+)\.([A-Z]+)$/);
  if (!other) return null;
  return { code: other[1]!, market: 0, exchange: other[2]! };
}

export function unwrapFuyao<T>(payload: Envelope<T>, fallbackMessage = "同花顺接口错误"): T {
  if (payload.code === 2001) {
    throw new Error("同花顺密匙无效或未填写，请在右上角重新输入");
  }
  if (payload.code === 2003) {
    throw new Error("同花顺密匙没有这个数据权限，请到扶摇后台开通 A 股能力");
  }
  if (payload.code !== 0) {
    throw new Error(payload.message || `${fallbackMessage} ${payload.code}`);
  }
  if (payload.data == null) {
    throw new Error("同花顺返回空数据");
  }
  return payload.data;
}

export function fuyaoErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "同花顺行情暂时不可用";
}

async function fuyaoGet<T>(path: string, apiKey: string, timeoutMs = 20000): Promise<T> {
  const key = apiKey.trim();
  if (!key) {
    throw new Error("请先填写同花顺密匙（右上角切换到同花顺后输入）");
  }
  const url = path.startsWith("http") ? path : `${FUYAO_BASE}${path}`;
  const response = await fetch(url, {
    cache: "no-store",
    headers: {
      "X-api-key": key,
      Accept: "application/json",
    },
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) {
    throw new Error(`同花顺接口 HTTP ${response.status}`);
  }
  const payload = (await response.json()) as Envelope<T>;
  return unwrapFuyao(payload);
}

async function mapPool<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let cursor = 0;
  const workers = Array.from({ length: Math.min(Math.max(limit, 1), items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      out[index] = await fn(items[index]!);
    }
  });
  await Promise.all(workers);
  return out;
}

export async function fetchThsCatalog(
  tag: "industry" | "cn_concept",
  apiKey: string,
): Promise<CatalogItem[]> {
  return cached(`ths:catalog:${tag}`, 60 * 60 * 1000, async () => {
    const data = await fuyaoGet<{ item?: CatalogItem[] }>(
      `/api/a-share-index/catalog/ths-index-list?tag=${tag}`,
      apiKey,
    );
    return (data.item ?? []).filter((item) => item.thscode && item.name);
  });
}

async function fetchPriceSnapshots(path: string, thscodes: string[], apiKey: string, chunk: number) {
  const unique = [...new Set(thscodes.filter(Boolean))];
  const batches = chunkList(unique, chunk);
  const items: PriceItem[] = [];
  for (const batch of batches) {
    const query = new URLSearchParams({ thscodes: batch.join(",") });
    const data = await fuyaoGet<{ item?: PriceItem[] }>(`${path}?${query.toString()}`, apiKey, 25000);
    items.push(...(data.item ?? []));
  }
  return items;
}

export async function fetchThsIndexSnapshots(thscodes: string[], apiKey: string): Promise<PriceItem[]> {
  return fetchPriceSnapshots("/api/a-share-index/prices/snapshot", thscodes, apiKey, SNAPSHOT_CHUNK);
}

export async function fetchThsStockSnapshots(thscodes: string[], apiKey: string): Promise<PriceItem[]> {
  return fetchPriceSnapshots("/api/a-share/prices/snapshot", thscodes, apiKey, STOCK_CHUNK);
}

export async function fetchThsConstituents(thscode: string, apiKey: string): Promise<CatalogItem[]> {
  return cached(`ths:members:${thscode}`, 8 * 60 * 1000, async () => {
    const data = await fuyaoGet<{ item?: CatalogItem[] }>(
      `/api/a-share-index/constituents/ths-stock-list?thscode=${encodeURIComponent(thscode)}`,
      apiKey,
    );
    return (data.item ?? []).filter((item) => item.thscode);
  });
}

async function fetchPagedItems<T>(
  path: string,
  apiKey: string,
  extraQuery = "",
): Promise<{ timestamp: number; items: T[]; total: number }> {
  const firstPath = extraQuery ? `${path}?${extraQuery}&page=1&size=200` : `${path}?page=1&size=200`;
  const first = await fuyaoGet<PageData<T>>(firstPath, apiKey);
  const items = [...(first.item ?? [])];
  const pages = first.pagination?.pages ?? 1;
  for (let page = 2; page <= pages; page += 1) {
    const nextPath = extraQuery
      ? `${path}?${extraQuery}&page=${page}&size=200`
      : `${path}?page=${page}&size=200`;
    const next = await fuyaoGet<PageData<T>>(nextPath, apiKey);
    items.push(...(next.item ?? []));
  }
  return {
    timestamp: first.timestamp ?? Date.now(),
    items,
    total: first.pagination?.total ?? items.length,
  };
}

function tickerOf(item: { thscode?: string; ticker?: string }): string {
  if (item.ticker && /^\d{6}$/.test(item.ticker)) return item.ticker;
  return parseThsCode(item.thscode)?.code ?? "";
}

export function limitUpToZt(item: LimitUpItem): ZtInfo | null {
  const code = tickerOf(item);
  if (!code) return null;
  const firstSealTime = parseHhMmToFbt(item.limit_up_time);
  return {
    code,
    name: asString(item.name) ?? code,
    firstSealTime,
    lastSealTime: firstSealTime,
    consecutiveBoards: asNumber(item.continue_day_cnt) ?? 1,
    sealAmount: asNumber(item.seal_money),
    openCount: 0,
    ztDays: asNumber(item.continue_day_cnt) ?? 0,
    ztBoards: asNumber(item.continue_day_cnt) ?? 0,
    industry: null,
  };
}

export function limitBreakToZb(item: LimitBreakItem): ZbInfo | null {
  const code = tickerOf(item);
  if (!code) return null;
  return {
    code,
    name: asString(item.name) ?? code,
    firstSealTime: 0,
    openCount: asNumber(item.open_times) ?? 1,
    changePercent: asNumber(item.price_change_ratio_pct),
    industry: null,
  };
}

function toBoardQuote(meta: CatalogItem, snap: PriceItem | undefined, kind: BoardKind): BoardQuote {
  return {
    code: meta.thscode,
    name: meta.name,
    kind,
    price: asNumber(snap?.last_price),
    changePercent: asNumber(snap?.price_change_ratio_pct),
    amount: asNumber(snap?.turnover),
    turnoverRate: null,
    mainNetInflow: null,
    mainNetInflowPercent: null,
    upCount: null,
    downCount: null,
    leadName: null,
    leadCode: null,
    leadChangePercent: null,
  };
}

function toStockQuote(meta: CatalogItem, snap: PriceItem | undefined): StockQuote | null {
  const parsed = parseThsCode(meta.thscode);
  if (!parsed) return null;
  const name = asString(meta.name) ?? asString(snap?.name) ?? parsed.code;
  if (isStStock(name)) return null;
  return {
    code: parsed.code,
    name,
    market: parsed.market,
    price: asNumber(snap?.last_price),
    changePercent: asNumber(snap?.price_change_ratio_pct),
    amount: asNumber(snap?.turnover),
    turnoverRate: null,
    high: asNumber(snap?.high_price),
    low: asNumber(snap?.low_price),
    open: asNumber(snap?.open_price),
    speed: null,
    mainNetInflow: null,
  };
}

function toIndexQuote(meta: { thscode: string; name: string }, snap: PriceItem | undefined): IndexQuote {
  const parsed = parseThsCode(meta.thscode);
  return {
    code: parsed?.code ?? meta.thscode,
    name: meta.name,
    price: asNumber(snap?.last_price),
    changePercent: asNumber(snap?.price_change_ratio_pct),
    change: asNumber(snap?.price_change),
    amount: asNumber(snap?.turnover),
    upCount: null,
    downCount: null,
    flatCount: null,
  };
}

async function loadThsBoards(kind: BoardKind, apiKey: string): Promise<BoardQuote[]> {
  const tag = kind === "concept" ? "cn_concept" : "industry";
  const catalog = (await fetchThsCatalog(tag, apiKey)).filter((item) => !isNoiseBoard(item.name));
  if (!catalog.length) return [];
  const snaps = await fetchThsIndexSnapshots(
    catalog.map((item) => item.thscode),
    apiKey,
  );
  const byCode = new Map(snaps.map((item) => [item.thscode, item]));
  return catalog
    .map((item) => toBoardQuote(item, byCode.get(item.thscode), kind))
    .filter((board) => board.changePercent != null);
}

function sortBoards(boards: BoardQuote[], sort: SectorSort): BoardQuote[] {
  const copy = [...boards];
  copy.sort((a, b) => {
    if (sort === "amount" || sort === "inflow") return (b.amount ?? 0) - (a.amount ?? 0);
    return (b.changePercent ?? Number.NEGATIVE_INFINITY) - (a.changePercent ?? Number.NEGATIVE_INFINITY);
  });
  return copy;
}

export type ThsSnapshotQuery = {
  universe: Universe;
  sort: SectorSort;
};

export async function buildThsSnapshot(query: ThsSnapshotQuery, apiKey: string): Promise<MarketSnapshot> {
  const { universe, sort } = query;
  const session = getMarketSession();
  const [conceptBoards, industryBoards, indexSnaps, ztPage, zbPage] = await Promise.all([
    universe === "industry" ? Promise.resolve([] as BoardQuote[]) : loadThsBoards("concept", apiKey),
    universe === "concept" ? Promise.resolve([] as BoardQuote[]) : loadThsBoards("industry", apiKey),
    fetchThsIndexSnapshots(
      INDEX_LIST.map((item) => item.thscode),
      apiKey,
    ),
    fetchPagedItems<LimitUpItem>(
      "/api/a-share/special-data/limit-up-pool",
      apiKey,
      "sort_field=limit_up_time&sort_dir=asc",
    ),
    fetchPagedItems<LimitBreakItem>(
      "/api/a-share/special-data/limit-break-pool",
      apiKey,
      "sort_field=open_times&sort_dir=desc",
    ),
  ]);

  const ztPool = ztPage.items
    .filter((item) => !item.is_st && !isStStock(asString(item.name) ?? ""))
    .map(limitUpToZt)
    .filter((item): item is ZtInfo => Boolean(item));
  const zbPool = zbPage.items.map(limitBreakToZb).filter((item): item is ZbInfo => Boolean(item));
  const ztByCode = new Map(ztPool.map((item) => [item.code, item]));
  const zbByCode = new Map(zbPool.map((item) => [item.code, item]));

  const indexByCode = new Map(indexSnaps.map((item) => [item.thscode, item]));
  const indices = INDEX_LIST.map((meta) => toIndexQuote(meta, indexByCode.get(meta.thscode)));

  const effectiveSort: SectorSort = sort === "inflow" ? "amount" : sort;
  const filtered = sortBoards([...conceptBoards, ...industryBoards], effectiveSort === "limitUp" ? "change" : effectiveSort);
  const candidateCount = sort === "limitUp" ? 14 : 10;
  const candidates = filtered.slice(0, candidateCount);

  const enriched = await mapPool(candidates, 4, async (board) => {
    const membersMeta = await fetchThsConstituents(board.code, apiKey);
    const snaps = await fetchThsStockSnapshots(
      membersMeta.map((item) => item.thscode),
      apiKey,
    );
    const snapByCode = new Map(snaps.map((item) => [item.thscode, item]));
    const members = membersMeta
      .map((item) => toStockQuote(item, snapByCode.get(item.thscode)))
      .filter((item): item is StockQuote => item != null && item.price != null && item.changePercent != null);
    const leaders = rankLeaders(members, ztByCode, zbByCode, 3);
    const limitUpCount = members.filter((item) => ztByCode.has(item.code)).length;
    const brokenCount = members.filter((item) => !ztByCode.has(item.code) && zbByCode.has(item.code)).length;
    return {
      board,
      leaders,
      memberCount: members.length,
      limitUpCount,
      brokenCount,
    };
  });

  const usable = enriched.filter((item) => item.memberCount >= 4);
  const ranked =
    sort === "limitUp"
      ? [...usable].sort((a, b) => {
          if (b.limitUpCount !== a.limitUpCount) return b.limitUpCount - a.limitUpCount;
          return (b.board.changePercent ?? 0) - (a.board.changePercent ?? 0);
        })
      : usable;

  const top = ranked.slice(0, 3);
  const sectors: SectorSnapshot[] = top.map((item, index) => ({
    rank: index + 1,
    code: item.board.code,
    name: item.board.name,
    kind: item.board.kind,
    changePercent: item.board.changePercent,
    amount: item.board.amount,
    mainNetInflow: item.board.mainNetInflow,
    upCount: item.board.upCount,
    downCount: item.board.downCount,
    memberCount: item.memberCount,
    limitUpCount: item.limitUpCount,
    brokenCount: item.brokenCount,
    trend: [],
    leaders: item.leaders.map((leader) => ({ ...leader, trend: [] })),
  }));

  const marketLeaders = rankMarketLeaders(ztPool).map((leader) => ({ ...leader, trend: [] }));

  const tradeDate = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
    .format(new Date(ztPage.timestamp || Date.now()))
    .replaceAll("-", "");

  return {
    tradeDate,
    updatedAt: new Date().toISOString(),
    session,
    universe,
    sort,
    source: "ths",
    indices,
    ztCount: ztPage.total,
    zbCount: zbPage.total,
    marketLeaders,
    sectors,
    error:
      sort === "inflow"
        ? "同花顺快照暂无主力净流入，已按成交额排序"
        : undefined,
  };
}
