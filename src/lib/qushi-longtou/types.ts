import type { BoardKind, DataSource, IndexQuote, MarketSession, SectorSort, Universe } from "../types";

export type TrendCriterion =
  | "方向明确"
  | "均线支撑"
  | "量价配合"
  | "回调浅"
  | "板块有配合";

export const TREND_CRITERIA: TrendCriterion[] = [
  "方向明确",
  "均线支撑",
  "量价配合",
  "回调浅",
  "板块有配合",
];

export const CRITERION_HINTS: Record<TrendCriterion, string> = {
  方向明确: "上涨方向清楚，收盘靠近当日高位",
  均线支撑: "股价站在5日均线之上或贴近均线",
  量价配合: "上涨伴随换手与成交额，资金真实参与",
  回调浅: "日内从高点回落幅度有限",
  板块有配合: "所在板块整体走强，不是个股独舞",
};

export type TrendLeaderStock = {
  code: string;
  name: string;
  market: number;
  price: number | null;
  changePercent: number | null;
  amount: number | null;
  turnoverRate: number | null;
  score: number;
  checks: Record<TrendCriterion, boolean>;
  ma5: number | null;
  dayPullbackPct: number | null;
  reason: string;
};

export type TrendSectorSnapshot = {
  rank: number;
  code: string;
  name: string;
  kind: BoardKind;
  changePercent: number | null;
  amount: number | null;
  upCount: number | null;
  downCount: number | null;
  sectorSync: boolean;
  memberCount: number;
  leaders: TrendLeaderStock[];
};

export type QushiLongTouSnapshot = {
  tradeDate: string;
  updatedAt: string;
  session: MarketSession;
  universe: Universe;
  sort: SectorSort;
  source: DataSource;
  indices: IndexQuote[];
  ztCount: number;
  zbCount: number;
  sectors: TrendSectorSnapshot[];
  error?: string;
};
