import { fetchBoards, fetchConstituents, fetchIndices, fetchZbPool, fetchZtPool } from "../eastmoney";
import { beijingYmd, isTodayYmd } from "../format";
import { getMarketSession } from "../market-hours";
import { isNoiseBoard } from "../noise-boards";
import type { BoardQuote, DataSource, SectorSort, Universe } from "../types";
import { classifySectorRoles } from "./roles";
import type { LT88Snapshot } from "./types";

export type LT88Query = {
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

function replayNote(): string {
  return "复盘模式：涨停/炸板池为所选日期，板块行情仍为实时数据";
}

export function parseLT88Query(searchParams: URLSearchParams): LT88Query {
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

export async function buildLT88Snapshot(query: LT88Query): Promise<LT88Snapshot> {
  if (query.source !== "eastmoney") {
    return emptyLT88(query, "龙头88 当前仅支持东方财富数据源");
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
  const zbByCode = new Map(zbPool.pool.map((item) => [item.code, item]));

  const filtered = sortBoards(
    [...conceptBoards, ...industryBoards].filter(
      (board) => !isNoiseBoard(board.name) && memberFloor(board) >= 4,
    ),
    query.sort === "limitUp" ? "change" : query.sort,
  );

  const candidateCount = query.sort === "limitUp" ? 12 : 6;
  const candidates = filtered.slice(0, candidateCount);

  const enriched = await Promise.all(
    candidates.map(async (board) => {
      const members = await fetchConstituents(board.code);
      const limitUpCount = members.filter((item) => ztByCode.has(item.code)).length;
      const brokenCount = members.filter(
        (item) => !ztByCode.has(item.code) && zbByCode.has(item.code),
      ).length;
      return {
        board,
        members,
        limitUpCount,
        brokenCount,
      };
    }),
  );

  const ranked =
    query.sort === "limitUp"
      ? [...enriched].sort((a, b) => {
          if (b.limitUpCount !== a.limitUpCount) return b.limitUpCount - a.limitUpCount;
          return (b.board.changePercent ?? 0) - (a.board.changePercent ?? 0);
        })
      : enriched;

  const top = ranked.slice(0, 3);

  const sectors = top.map((item, index) => ({
    rank: index + 1,
    code: item.board.code,
    name: item.board.name,
    kind: item.board.kind,
    changePercent: item.board.changePercent,
    amount: item.board.amount,
    mainNetInflow: item.board.mainNetInflow,
    limitUpCount: item.limitUpCount,
    brokenCount: item.brokenCount,
    memberCount: item.members.length,
    roles: classifySectorRoles(item.members, ztByCode, zbByCode),
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
    error: replay ? replayNote() : undefined,
  };
}

function emptyLT88(query: LT88Query, error: string): LT88Snapshot {
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
