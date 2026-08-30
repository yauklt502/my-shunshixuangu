import { fetchBoards, fetchConstituents, fetchIndices, fetchTrendsMany, fetchZbPool, fetchZtPool } from "./eastmoney";
import { buildThsSnapshot, fuyaoErrorMessage } from "./fuyao";
import { buildTdxHqSnapshot, buildTdxLocalSnapshot } from "./tdx-snapshot";
import { getMarketSession } from "./market-hours";
import { isNoiseBoard } from "./noise-boards";
import { rankLeaders, rankMarketLeaders } from "./ranking";
import type {
  BoardQuote,
  DataSource,
  MarketSnapshot,
  SectorSort,
  SectorSnapshot,
  Universe,
} from "./types";

export type SnapshotQuery = {
  universe: Universe;
  sort: SectorSort;
  source: DataSource;
};

export type SnapshotOptions = {
  fuyaoKey?: string;
  tdxVipdoc?: string;
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
  return `${query.source}:${query.universe}:${query.sort}`;
}

function isKeyError(message: string | undefined): boolean {
  return Boolean(message && message.includes("密匙"));
}

function emptySnapshot(query: SnapshotQuery, error: string): MarketSnapshot {
  return {
    tradeDate: "",
    updatedAt: new Date().toISOString(),
    session: getMarketSession(),
    universe: query.universe,
    sort: query.sort,
    source: query.source,
    indices: [],
    ztCount: 0,
    zbCount: 0,
    marketLeaders: [],
    sectors: [],
    error,
  };
}

export async function buildSnapshot(
  query: SnapshotQuery,
  options: SnapshotOptions = {},
): Promise<MarketSnapshot> {
  const key = queryKey(query);
  try {
    const snapshot =
      query.source === "ths"
        ? await assembleThsSnapshot(query, options.fuyaoKey)
        : query.source === "tdx-hq"
          ? await buildTdxHqSnapshot(query.universe, query.sort)
          : query.source === "tdx-local"
            ? await buildTdxLocalSnapshot(query.universe, query.sort, options.tdxVipdoc)
            : await assembleSnapshot(query);
    if (snapshot.sectors.length) lastGood.set(key, snapshot);
    else {
      const prev = lastGood.get(key);
      if (prev && !isKeyError(snapshot.error)) {
        return { ...prev, updatedAt: new Date().toISOString(), error: snapshot.error || "行情暂无新数据，显示上次结果" };
      }
    }
    return snapshot;
  } catch (error) {
    const message = error instanceof Error ? error.message : "行情刷新失败，显示上次数据";
    const prev = lastGood.get(key);
    if (prev && !isKeyError(message)) {
      return {
        ...prev,
        updatedAt: new Date().toISOString(),
        error: `行情刷新失败，显示上次数据：${message}`,
      };
    }
    if (isKeyError(message)) return emptySnapshot(query, message);
    throw error;
  }
}

async function assembleThsSnapshot(query: SnapshotQuery, fuyaoKey?: string): Promise<MarketSnapshot> {
  const apiKey = (fuyaoKey ?? process.env.FUYAO_API_KEY ?? "").trim();
  if (!apiKey) {
    return emptySnapshot(query, "请先填写同花顺密匙（右上角切换到同花顺后输入，只保存在本机）");
  }
  try {
    return await buildThsSnapshot(query, apiKey);
  } catch (error) {
    throw new Error(fuyaoErrorMessage(error));
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

  const marketLeaders = rankMarketLeaders(ztPool.pool).map((leader) => ({ ...leader, trend: [] }));

  return {
    tradeDate: ztPool.qdate || zbPool.qdate,
    updatedAt: new Date().toISOString(),
    session,
    universe,
    sort,
    source: "eastmoney",
    indices,
    ztCount: ztPool.tc,
    zbCount: zbPool.tc,
    marketLeaders,
    sectors,
  };
}

export function parseSnapshotQuery(searchParams: URLSearchParams): SnapshotQuery {
  const universeRaw = searchParams.get("universe") ?? "all";
  const sortRaw = searchParams.get("sort") ?? "change";
  const sourceRaw = searchParams.get("source") ?? "eastmoney";
  const universe: Universe =
    universeRaw === "concept" || universeRaw === "industry" || universeRaw === "all"
      ? universeRaw
      : "all";
  const sort: SectorSort =
    sortRaw === "limitUp" || sortRaw === "amount" || sortRaw === "inflow" || sortRaw === "change"
      ? sortRaw
      : "change";
  const source: DataSource =
    sourceRaw === "ths" || sourceRaw === "tonghuashun" || sourceRaw === "fuyao"
      ? "ths"
      : sourceRaw === "tdx-hq" || sourceRaw === "tdx-realtime" || sourceRaw === "tongdaxin-hq"
        ? "tdx-hq"
        : sourceRaw === "tdx-local" || sourceRaw === "tdx" || sourceRaw === "tongdaxin"
          ? "tdx-local"
          : "eastmoney";
  return { universe, sort, source };
}
