import { fetchBoards, fetchConstituents, fetchIndices, fetchTrendsMany, fetchZbPool, fetchZtPool } from "./eastmoney";
import { getMarketSession } from "./market-hours";
import { isNoiseBoard } from "./noise-boards";
import { rankLeaders } from "./ranking";
import type {
  BoardQuote,
  MarketSnapshot,
  SectorSort,
  SectorSnapshot,
  Universe,
} from "./types";

export type SnapshotQuery = {
  universe: Universe;
  sort: SectorSort;
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

const lastGood = new Map<string, MarketSnapshot>();

function queryKey(query: SnapshotQuery): string {
  return `${query.universe}:${query.sort}`;
}

export async function buildSnapshot(query: SnapshotQuery): Promise<MarketSnapshot> {
  const key = queryKey(query);
  try {
    const snapshot = await assembleSnapshot(query);
    if (snapshot.sectors.length) lastGood.set(key, snapshot);
    else {
      const prev = lastGood.get(key);
      if (prev) {
        return { ...prev, updatedAt: new Date().toISOString(), error: "行情暂无新数据，显示上次结果" };
      }
    }
    return snapshot;
  } catch (error) {
    const prev = lastGood.get(key);
    if (prev) {
      return {
        ...prev,
        updatedAt: new Date().toISOString(),
        error: error instanceof Error ? `行情刷新失败，显示上次数据：${error.message}` : "行情刷新失败，显示上次数据",
      };
    }
    throw error;
  }
}

async function assembleSnapshot(query: SnapshotQuery): Promise<MarketSnapshot> {
  const { universe, sort } = query;
  const session = getMarketSession();

  const [indices, conceptBoards, industryBoards, ztPool, zbPool] = await Promise.all([
    fetchIndices(),
    universe === "industry" ? Promise.resolve([]) : fetchBoards("concept"),
    universe === "concept" ? Promise.resolve([]) : fetchBoards("industry"),
    fetchZtPool(),
    fetchZbPool(),
  ]);

  const ztByCode = new Map(ztPool.pool.map((item) => [item.code, item]));
  const zbByCode = new Map(zbPool.pool.map((item) => [item.code, item]));

  const filtered = sortBoards(
    [...conceptBoards, ...industryBoards].filter(
      (board) => !isNoiseBoard(board.name) && memberFloor(board) >= 4,
    ),
    sort === "limitUp" ? "change" : sort,
  );

  const candidateCount = sort === "limitUp" ? 12 : 6;
  const candidates = filtered.slice(0, candidateCount);

  const enriched = await Promise.all(
    candidates.map(async (board) => {
      const members = await fetchConstituents(board.code);
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
    }),
  );

  const ranked =
    sort === "limitUp"
      ? [...enriched].sort((a, b) => {
          if (b.limitUpCount !== a.limitUpCount) return b.limitUpCount - a.limitUpCount;
          return (b.board.changePercent ?? 0) - (a.board.changePercent ?? 0);
        })
      : enriched;

  const top = ranked.slice(0, 3);
  const trendIds = top.map((item) => `90.${item.board.code}`);
  const trends = await fetchTrendsMany(trendIds);

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
    trend: trends[`90.${item.board.code}`] ?? [],
    leaders: item.leaders.map((leader) => ({
      ...leader,
      trend: [],
    })),
  }));

  return {
    tradeDate: ztPool.qdate || zbPool.qdate,
    updatedAt: new Date().toISOString(),
    session,
    universe,
    sort,
    indices,
    ztCount: ztPool.tc,
    zbCount: zbPool.tc,
    sectors,
  };
}

export function parseSnapshotQuery(searchParams: URLSearchParams): SnapshotQuery {
  const universeRaw = searchParams.get("universe") ?? "all";
  const sortRaw = searchParams.get("sort") ?? "change";
  const universe: Universe =
    universeRaw === "concept" || universeRaw === "industry" || universeRaw === "all"
      ? universeRaw
      : "all";
  const sort: SectorSort =
    sortRaw === "limitUp" || sortRaw === "amount" || sortRaw === "inflow" || sortRaw === "change"
      ? sortRaw
      : "change";
  return { universe, sort };
}
