import { beijingYmd, isTodayYmd } from "./format";
import { getMarketSession } from "./market-hours";
import { isNoiseBoard, isStStock } from "./noise-boards";
import { rankLeaders, rankMarketLeaders } from "./ranking";
import {
  connectTdxHq,
  tdxHqAllSecurities,
  tdxHqDownloadBlock,
  tdxHqQuotes,
} from "./tdx-hq";
import { readLocalBlocks, readManyDayQuotes, resolveTdxPaths, tdxLocalAvailable } from "./tdx-local";
import {
  changePercent,
  eastmoneyMarket,
  isLimitHigh,
  isLimitUpPrice,
  marketFromCode,
  type TdxBlock,
  type TdxHqQuote,
} from "./tdx-codec";
import type {
  BoardKind,
  BoardQuote,
  IndexQuote,
  MarketSnapshot,
  SectorSort,
  SectorSnapshot,
  StockQuote,
  Universe,
  ZbInfo,
  ZtInfo,
} from "./types";

const INDEXES = [
  { code: "000001", market: 1, name: "上证指数" },
  { code: "399001", market: 0, name: "深证成指" },
  { code: "399006", market: 0, name: "创业板指" },
  { code: "000688", market: 1, name: "科创50" },
];

function matchBlock(blocks: TdxBlock[], name: string): TdxBlock | undefined {
  const needle = name.trim();
  return (
    blocks.find((block) => block.name === needle) ||
    blocks.find((block) => block.name.startsWith(needle) || needle.startsWith(block.name))
  );
}

function toStock(quote: TdxHqQuote, name: string): StockQuote {
  return {
    code: quote.code,
    name,
    market: eastmoneyMarket(quote.code),
    price: quote.price,
    changePercent: changePercent(quote.price, quote.lastClose),
    amount: quote.amount,
    turnoverRate: null,
    high: quote.high,
    low: quote.low,
    open: quote.open,
    speed: null,
    mainNetInflow: null,
  };
}

function ztFromQuote(quote: TdxHqQuote, name: string): ZtInfo | null {
  if (!isLimitUpPrice(quote.code, name, quote.price, quote.lastClose)) return null;
  return {
    code: quote.code,
    name,
    firstSealTime: 0,
    lastSealTime: 0,
    consecutiveBoards: 1,
    sealAmount: null,
    openCount: 0,
    ztDays: 1,
    ztBoards: 1,
    industry: null,
  };
}

function zbFromQuote(quote: TdxHqQuote, name: string): ZbInfo | null {
  if (isLimitUpPrice(quote.code, name, quote.price, quote.lastClose)) return null;
  if (!isLimitHigh(quote.code, name, quote.high, quote.lastClose)) return null;
  return {
    code: quote.code,
    name,
    firstSealTime: 0,
    openCount: 1,
    changePercent: changePercent(quote.price, quote.lastClose),
    industry: null,
  };
}

function boardChange(quotes: TdxHqQuote[]): { changePercent: number | null; amount: number; up: number; down: number } {
  let amount = 0;
  let up = 0;
  let down = 0;
  const pcts: number[] = [];
  for (const quote of quotes) {
    amount += quote.amount || 0;
    const pct = changePercent(quote.price, quote.lastClose);
    if (pct == null) continue;
    pcts.push(pct);
    if (pct > 0) up += 1;
    else if (pct < 0) down += 1;
  }
  const avg = pcts.length ? pcts.reduce((a, b) => a + b, 0) / pcts.length : null;
  return { changePercent: avg, amount, up, down };
}

function sortBoards(boards: BoardQuote[], sort: SectorSort): BoardQuote[] {
  const copy = [...boards];
  copy.sort((a, b) => {
    if (sort === "amount" || sort === "inflow") return (b.amount ?? 0) - (a.amount ?? 0);
    return (b.changePercent ?? Number.NEGATIVE_INFINITY) - (a.changePercent ?? Number.NEGATIVE_INFINITY);
  });
  return copy;
}

function assembleFromQuotes(args: {
  universe: Universe;
  sort: SectorSort;
  source: "tdx-local" | "tdx-hq";
  blocks: TdxBlock[];
  names: Map<string, string>;
  indexQuotes: TdxHqQuote[];
  quoteOf: (codes: string[]) => Map<string, TdxHqQuote>;
  tradeDate: string;
  error?: string;
}): MarketSnapshot {
  const { universe, sort, source, blocks, names, indexQuotes, quoteOf, tradeDate, error } = args;
  const replay = !isTodayYmd(tradeDate);
  const filtered = blocks.filter((block) => {
    if (isNoiseBoard(block.name)) return false;
    if (universe === "concept" && block.kind !== "concept") return false;
    if (universe === "industry" && block.kind !== "industry") return false;
    return block.codes.length >= 4;
  });

  const boardQuotes: BoardQuote[] = filtered.map((block) => {
    const memberQuotes = [...quoteOf(block.codes).values()];
    const stats = boardChange(memberQuotes);
    return {
      code: `${block.kind}:${block.name}`,
      name: block.name,
      kind: block.kind as BoardKind,
      price: null,
      changePercent: stats.changePercent,
      amount: stats.amount,
      turnoverRate: null,
      mainNetInflow: null,
      mainNetInflowPercent: null,
      upCount: stats.up,
      downCount: stats.down,
      leadName: null,
      leadCode: null,
      leadChangePercent: null,
    };
  }).filter((board) => board.changePercent != null);

  const effectiveSort: SectorSort = sort === "inflow" ? "amount" : sort;
  const rankedBoards = sortBoards(boardQuotes, effectiveSort === "limitUp" ? "change" : effectiveSort);
  const take = sort === "limitUp" ? 14 : 10;
  const candidates = rankedBoards.slice(0, take);

  const blockByKey = new Map(filtered.map((block) => [`${block.kind}:${block.name}`, block]));
  const enriched = candidates.map((board) => {
    const block = blockByKey.get(board.code);
    const memberCodes = block?.codes ?? [];
    const qmap = quoteOf(memberCodes);
    const members = memberCodes
      .map((code) => {
        const quote = qmap.get(code);
        if (!quote) return null;
        const name = names.get(code) || code;
        if (isStStock(name)) return null;
        return toStock(quote, name);
      })
      .filter((item): item is StockQuote => item != null && item.price != null && item.changePercent != null);
    if (members.length < 4) return null;
    const ztByCode = new Map<string, ZtInfo>();
    const zbByCode = new Map<string, ZbInfo>();
    for (const member of members) {
      const quote = qmap.get(member.code);
      if (!quote) continue;
      const zt = ztFromQuote(quote, member.name);
      if (zt) ztByCode.set(member.code, zt);
      const zb = zbFromQuote(quote, member.name);
      if (zb) zbByCode.set(member.code, zb);
    }
    const leaders = rankLeaders(members, ztByCode, zbByCode, 3).map((leader) => {
      if (leader.isLimitUp) {
        return { ...leader, reason: "通达信按涨停价判定（无先封时间）", sealKind: null, firstSealTime: null };
      }
      if (leader.isBroken) {
        return { ...leader, reason: "通达信按最高价触及涨停判定炸板", firstSealTime: null };
      }
      return leader;
    });
    return {
      board,
      memberCount: members.length,
      limitUpCount: members.filter((item) => ztByCode.has(item.code)).length,
      brokenCount: members.filter((item) => !ztByCode.has(item.code) && zbByCode.has(item.code)).length,
      leaders,
      ztByCode,
      zbByCode,
    };
  }).filter((item): item is NonNullable<typeof item> => Boolean(item));

  const ranked =
    sort === "limitUp"
      ? [...enriched].sort((a, b) => b.limitUpCount - a.limitUpCount || (b.board.changePercent ?? 0) - (a.board.changePercent ?? 0))
      : enriched;

  const top = ranked.slice(0, 3);
  const allZt = new Set(ranked.flatMap((item) => [...item.ztByCode.keys()]));
  const allZb = new Set(ranked.flatMap((item) => [...item.zbByCode.keys()]));

  const marketZt: ZtInfo[] = [];
  const marketStocks = new Map<string, StockQuote>();
  for (const item of ranked) {
    for (const [code, zt] of item.ztByCode) {
      marketZt.push({ ...zt, industry: zt.industry || item.board.name });
    }
    for (const leader of item.leaders) {
      if (!leader.isLimitUp) continue;
      marketStocks.set(leader.code, {
        code: leader.code,
        name: leader.name,
        market: leader.market,
        price: leader.price,
        changePercent: leader.changePercent,
        amount: leader.amount,
        turnoverRate: leader.turnoverRate,
        speed: leader.speed,
        mainNetInflow: leader.mainNetInflow,
        high: null,
        low: null,
        open: null,
      });
    }
  }
  const marketLeaders = rankMarketLeaders(marketZt, marketStocks).map((leader) => ({
    ...leader,
    reason:
      source === "tdx-local" || source === "tdx-hq"
        ? `${leader.sectorName ? `${leader.sectorName} · ` : "全市场 · "}通达信按涨停价判定（无先封时间）`
        : leader.reason,
    trend: [] as number[],
  }));

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

  const indices: IndexQuote[] = INDEXES.map((meta) => {
    const quote = indexQuotes.find((item) => item.code === meta.code && item.market === meta.market);
    return {
      code: meta.code,
      name: meta.name,
      price: quote?.price ?? null,
      changePercent: quote ? changePercent(quote.price, quote.lastClose) : null,
      change: quote ? quote.price - quote.lastClose : null,
      amount: quote?.amount ?? null,
      upCount: null,
      downCount: null,
      flatCount: null,
    };
  });

  return {
    tradeDate,
    updatedAt: new Date().toISOString(),
    session: replay ? "closed" : getMarketSession(),
    universe,
    sort,
    source,
    indices,
    ztCount: allZt.size,
    zbCount: allZb.size,
    marketLeaders,
    sectors,
    error:
      replay && source === "tdx-local"
        ? "复盘模式：通达信本地按所选交易日 vipdoc 日线回放"
        : sort === "inflow"
          ? "通达信没有主力净流入，已按成交额排序"
          : error,
  };
}

export async function buildTdxHqSnapshot(
  universe: Universe,
  sort: SectorSort,
  date = beijingYmd(),
): Promise<MarketSnapshot> {
  if (!isTodayYmd(date)) {
    return {
      tradeDate: date,
      updatedAt: new Date().toISOString(),
      session: "closed",
      universe,
      sort,
      source: "tdx-hq",
      indices: [],
      ztCount: 0,
      zbCount: 0,
      marketLeaders: [],
      sectors: [],
      error: "复盘模式：通达信实时仅支持当日，请改选东方财富或通达信本地",
    };
  }
  await connectTdxHq();
  const concepts = await tdxHqDownloadBlock("block_gn.dat");
  const industries = universe === "concept" ? [] : await tdxHqDownloadBlock("block.dat");
  const lists = await tdxHqAllSecurities();
  const names = new Map<string, string>();
  for (const item of [...lists.sh, ...lists.sz, ...lists.bj]) {
    if (item.name) names.set(item.code.trim(), item.name.trim());
  }
  const indexSecs = lists.sh.filter((item) => item.code.startsWith("88"));
  const blocks = [...concepts, ...industries];
  const wantedBlocks = blocks.filter((block) => {
    if (isNoiseBoard(block.name)) return false;
    if (universe === "concept" && block.kind !== "concept") return false;
    return block.codes.length >= 4;
  });

  const rankedSeeds = indexSecs.filter((item) => {
    if (!item.code.startsWith("88") || item.code.startsWith("888") || isNoiseBoard(item.name)) return false;
    if (universe === "industry") return /^880[3-9]/.test(item.code);
    if (universe === "concept") return item.code.startsWith("881") || /^880[45]/.test(item.code);
    return /^880[3-9]/.test(item.code) || item.code.startsWith("881") || /^880[45]/.test(item.code);
  });
  const seedQuotes = await tdxHqQuotes(rankedSeeds.map((item) => ({ market: 1, code: item.code })));
  const seedQ = new Map(seedQuotes.map((item) => [item.code, item]));
  const seedBoards: { block: TdxBlock; changePercent: number; amount: number }[] = [];
  for (const seed of rankedSeeds) {
    const block = matchBlock(wantedBlocks, seed.name);
    if (!block) continue;
    const quote = seedQ.get(seed.code);
    const pct = quote ? changePercent(quote.price, quote.lastClose) : null;
    if (pct == null) continue;
    seedBoards.push({ block, changePercent: pct, amount: quote?.amount ?? 0 });
  }

  const take = sort === "limitUp" ? 14 : 10;
  let uniqueSeeds: typeof seedBoards = [];
  const seen = new Set<string>();
  const sortedSeeds = [...seedBoards].sort((a, b) => {
    if (sort === "amount" || sort === "inflow") return b.amount - a.amount;
    return b.changePercent - a.changePercent;
  });
  for (const item of sortedSeeds) {
    const key = `${item.block.kind}:${item.block.name}`;
    if (seen.has(key)) continue;
    seen.add(key);
    uniqueSeeds.push(item);
  }

  if (uniqueSeeds.length < 6) {
    const sampleCodes = [...new Set(wantedBlocks.flatMap((block) => block.codes.slice(0, 8)))];
    const sampleQuotes = await tdxHqQuotes(sampleCodes.map((code) => ({ market: marketFromCode(code), code })));
    const sampleMap = new Map(sampleQuotes.map((item) => [item.code, item]));
    uniqueSeeds = wantedBlocks
      .map((block) => {
        const qs = block.codes
          .slice(0, 8)
          .map((code) => sampleMap.get(code))
          .filter((item): item is TdxHqQuote => Boolean(item));
        const stats = boardChange(qs);
        return stats.changePercent == null
          ? null
          : { block, changePercent: stats.changePercent, amount: stats.amount };
      })
      .filter((item): item is NonNullable<typeof item> => item != null)
      .sort((a, b) => {
        if (sort === "amount" || sort === "inflow") return b.amount - a.amount;
        return b.changePercent - a.changePercent;
      });
  }

  const useBlocks = uniqueSeeds.slice(0, take).map((item) => item.block);
  const memberCodes = [...new Set(useBlocks.flatMap((block) => block.codes))];
  const indexNeed = INDEXES.map((item) => ({ market: item.market, code: item.code }));
  const quotes = await tdxHqQuotes([
    ...memberCodes.map((code) => ({
      market: marketFromCode(code),
      code,
    })),
    ...indexNeed,
  ]);
  const qmap = new Map(quotes.map((item) => [item.code, item]));
  return assembleFromQuotes({
    universe,
    sort,
    source: "tdx-hq",
    blocks: useBlocks,
    names,
    indexQuotes: quotes.filter((item) => INDEXES.some((idx) => idx.code === item.code && idx.market === item.market)),
    tradeDate: date,
    quoteOf: (codes) => {
      const map = new Map<string, TdxHqQuote>();
      for (const code of codes) {
        const quote = qmap.get(code);
        if (quote) map.set(code, quote);
      }
      return map;
    },
  });
}

export async function buildTdxLocalSnapshot(
  universe: Universe,
  sort: SectorSort,
  vipdoc?: string,
  date = beijingYmd(),
): Promise<MarketSnapshot> {
  const paths = resolveTdxPaths(vipdoc || process.env.TDX_VIPDOC);
  const replay = !isTodayYmd(date);
  const avail = tdxLocalAvailable(paths);
  if (!avail.ok) {
    return {
      tradeDate: "",
      updatedAt: new Date().toISOString(),
      session: getMarketSession(),
      universe,
      sort,
      source: "tdx-local",
      indices: [],
      ztCount: 0,
      zbCount: 0,
      marketLeaders: [],
      sectors: [],
      error: avail.message,
    };
  }
  const blocks = readLocalBlocks(paths);
  if (!blocks.length) {
    return {
      tradeDate: "",
      updatedAt: new Date().toISOString(),
      session: getMarketSession(),
      universe,
      sort,
      source: "tdx-local",
      indices: [],
      ztCount: 0,
      zbCount: 0,
      marketLeaders: [],
      sectors: [],
      error: `找到了 vipdoc，但板块文件不在 ${paths.hqCache}。请确认 T0002\\hq_cache\\block_gn.dat 存在，或改用「通达信实时」。`,
    };
  }
  const wanted = blocks.filter((block) => {
    if (isNoiseBoard(block.name)) return false;
    if (universe === "concept" && block.kind !== "concept") return false;
    if (universe === "industry" && block.kind !== "industry") return false;
    return block.codes.length >= 4;
  });
  const seedCodes = [...new Set(wanted.flatMap((block) => block.codes.slice(0, 16)))];
  const seedMap = readManyDayQuotes(seedCodes, paths, date);
  const seeded = wanted
    .map((block) => {
      const quotes = block.codes.slice(0, 16).map((code) => seedMap.get(code)).filter((item): item is TdxHqQuote => Boolean(item));
      const stats = boardChange(quotes);
      return { block, changePercent: stats.changePercent, amount: stats.amount };
    })
    .filter((item) => item.changePercent != null);
  seeded.sort((a, b) => {
    if (sort === "amount" || sort === "inflow") return b.amount - a.amount;
    return (b.changePercent ?? 0) - (a.changePercent ?? 0);
  });
  const take = sort === "limitUp" ? 14 : 10;
  const useBlocks = seeded.slice(0, take).map((item) => item.block);
  const memberCodes = [...new Set(useBlocks.flatMap((block) => block.codes))];
  const qmap = readManyDayQuotes([...memberCodes, ...INDEXES.map((item) => item.code)], paths, date);
  const names = new Map<string, string>();
  const localNote = replay
    ? undefined
    : "通达信本地用的是 vipdoc 日线（最后两根K线），不是盘中 tick。盘中请选「通达信实时」。";
  return assembleFromQuotes({
    universe,
    sort,
    source: "tdx-local",
    blocks: useBlocks,
    names,
    indexQuotes: INDEXES.map((item) => qmap.get(item.code)).filter((item): item is TdxHqQuote => Boolean(item)),
    tradeDate: date,
    quoteOf: (codes) => {
      const map = new Map<string, TdxHqQuote>();
      for (const code of codes) {
        const quote = qmap.get(code);
        if (quote) map.set(code, quote);
      }
      return map;
    },
    error: localNote,
  });
}

export function matchBlockForTests(blocks: TdxBlock[], name: string) {
  return matchBlock(blocks, name);
}
