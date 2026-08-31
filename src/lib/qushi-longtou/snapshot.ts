import { fetchBoards, fetchConstituents, fetchIndices, fetchZbPool, fetchZtPool } from "../eastmoney";
import { beijingYmd, isTodayYmd } from "../format";
import { getMarketSession } from "../market-hours";
import { isNoiseBoard } from "../noise-boards";
import type { BoardQuote, DataSource, SectorSort, StockQuote, Universe } from "../types";
import { fetchClosesMany } from "./kline";
import { rankTrendLeaders, sectorHasSync } from "./score";
import type { QushiLongTouSnapshot } from "./types";

export type QLTQuery = {
  universe: Universe;
  sort: SectorSort;
  source: DataSource;
  date: string;
};

function sortBoards(boards: BoardQuote[], sort: SectorSort): BoardQuote[] {
  const copy = [...boards];
  copy.sort((a, b) => {
    if (sort === "amount") return (b.amount ?? 0) - (a.amount ?? 0);
    if (sort === "inflow") return (b.mainNetInflow ?? 0) - (a.mainNetInflow ?? 0);
    return (b.changePercent ?? Number.NEGATIVE_INFINITY) - (a.changePercent ?? Number.NEGATIVE_INFINITY);
  });
  return copy;
}

function memberFloor(board: BoardQuote): number {
  return (board.upCount ?? 0) + (board.downCount ?? 0);
}

function pickKlineCandidates(members: StockQuote[]): StockQuote[] {
  return members
    .filter((stock) => stock.changePercent !== null && stock.changePercent >= 1.5 && stock.changePercent < 9.9)
    .sort((a, b) => (b.changePercent ?? 0) - (a.changePercent ?? 0))
    .slice(0, 18);
}

export function parseQLTQuery(searchParams: URLSearchParams): QLTQuery {
  const universeRaw = searchParams.get("universe") ?? "all";
  const sortRaw = searchParams.get("sort") ?? "change";
  const sourceRaw = searchParams.get("source") ?? "eastmoney";
  const dateRaw = searchParams.get("date");
  const universe: Universe =
    universeRaw === "concept" || universeRaw === "industry" || universeRaw === "all"
      ? universeRaw
      : "all";
  const sort: SectorSort =
    sortRaw === "limitUp" || sortRaw === "amount" || sortRaw === "inflow" || sortRaw === "change"
      ? sortRaw
      : "change";
  const source: DataSource = sourceRaw === "eastmoney" ? "eastmoney" : "eastmoney";
  const normalized = dateRaw?.replaceAll("-", "").trim();
  const date = normalized && /^\d{8}$/.test(normalized) ? normalized : beijingYmd();
  return { universe, sort, source, date };
}

export async function buildQLTSnapshot(query: QLTQuery): Promise<QushiLongTouSnapshot> {
  if (query.source !== "eastmoney") {
    return emptyQLT(query, "趋势龙头 当前仅支持东方财富数据源");
  }

  const replay = !isTodayYmd(query.date);
  const session = replay ? "closed" : getMarketSession();

  const [indices, conceptBoards, industryBoards, ztPool, zbPool] = await Promise.all([
    fetchIndices(),
    query.universe === "industry" ? Promise.resolve([]) : fetchBoards("concept"),
    query.universe === "concept" ? Promise.resolve([]) : fetchBoards("industry"),
    fetchZtPool(query.date),
    fetchZbPool(query.date),
  ]);

  const ztByCode = new Map(ztPool.pool.map((item) => [item.code, item]));

  const filtered = sortBoards(
    [...conceptBoards, ...industryBoards].filter(
      (board) => !isNoiseBoard(board.name) && memberFloor(board) >= 4,
    ),
    query.sort === "limitUp" ? "change" : query.sort,
  );

  const candidates = filtered.slice(0, 6);
  const enriched = await Promise.all(
    candidates.map(async (board) => {
      const members = await fetchConstituents(board.code);
      const klineTargets = pickKlineCandidates(members);
      const closesByCode = await fetchClosesMany(
        klineTargets.map((stock) => ({ market: stock.market, code: stock.code })),
      );
      const leaders = rankTrendLeaders(members, board, closesByCode, ztByCode, 5);
      return { board, members, leaders };
    }),
  );

  const ranked =
    query.sort === "limitUp"
      ? [...enriched].sort((a, b) => {
          const aUp = a.members.filter((item) => ztByCode.has(item.code)).length;
          const bUp = b.members.filter((item) => ztByCode.has(item.code)).length;
          if (bUp !== aUp) return bUp - aUp;
          return (b.board.changePercent ?? 0) - (a.board.changePercent ?? 0);
        })
      : enriched;

  const sectors = ranked.slice(0, 3).map((item, index) => ({
    rank: index + 1,
    code: item.board.code,
    name: item.board.name,
    kind: item.board.kind,
    changePercent: item.board.changePercent,
    amount: item.board.amount,
    upCount: item.board.upCount,
    downCount: item.board.downCount,
    sectorSync: sectorHasSync(item.board, item.members),
    memberCount: item.members.length,
    leaders: item.leaders,
  }));

  return {
    tradeDate: ztPool.qdate || zbPool.qdate || query.date,
    updatedAt: new Date().toISOString(),
    session,
    universe: query.universe,
    sort: query.sort,
    source: "eastmoney",
    indices,
    ztCount: ztPool.tc,
    zbCount: zbPool.tc,
    sectors,
    error: replay ? "复盘模式：涨停池为所选日期，板块与均线为实时数据" : undefined,
  };
}

function emptyQLT(query: QLTQuery, error: string): QushiLongTouSnapshot {
  return {
    tradeDate: query.date,
    updatedAt: new Date().toISOString(),
    session: "closed",
    universe: query.universe,
    sort: query.sort,
    source: query.source,
    indices: [],
    ztCount: 0,
    zbCount: 0,
    sectors: [],
    error,
  };
}
