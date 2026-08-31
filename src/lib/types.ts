export type Universe = "concept" | "industry" | "all";
export type SectorSort = "change" | "limitUp" | "amount" | "inflow";
export type DataSource = "eastmoney" | "ths" | "tdx-local" | "tdx-hq";

export type MarketSession =
  | "pre"
  | "auction"
  | "morning"
  | "lunch"
  | "afternoon"
  | "closed"
  | "weekend";

export type BoardKind = "concept" | "industry";

export type LeaderRank = "龙一" | "龙二" | "龙三";

export type MarketLeaderRank = "总龙头" | "龙二" | "龙三";

export type IndexQuote = {
  code: string;
  name: string;
  price: number | null;
  changePercent: number | null;
  change: number | null;
  amount: number | null;
  upCount: number | null;
  downCount: number | null;
  flatCount: number | null;
};

export type BoardQuote = {
  code: string;
  name: string;
  kind: BoardKind;
  price: number | null;
  changePercent: number | null;
  amount: number | null;
  turnoverRate: number | null;
  mainNetInflow: number | null;
  mainNetInflowPercent: number | null;
  upCount: number | null;
  downCount: number | null;
  leadName: string | null;
  leadCode: string | null;
  leadChangePercent: number | null;
};

export type StockQuote = {
  code: string;
  name: string;
  market: number;
  price: number | null;
  changePercent: number | null;
  amount: number | null;
  turnoverRate: number | null;
  high: number | null;
  low: number | null;
  open: number | null;
  speed: number | null;
  mainNetInflow: number | null;
};

export type ZtInfo = {
  code: string;
  name: string;
  firstSealTime: number;
  lastSealTime: number;
  consecutiveBoards: number;
  sealAmount: number | null;
  openCount: number;
  ztDays: number;
  ztBoards: number;
  industry: string | null;
};

export type ZbInfo = {
  code: string;
  name: string;
  firstSealTime: number;
  openCount: number;
  changePercent: number | null;
  industry: string | null;
};

export type RankedLeader = {
  rank: LeaderRank;
  code: string;
  name: string;
  market: number;
  price: number | null;
  changePercent: number | null;
  amount: number | null;
  turnoverRate: number | null;
  speed: number | null;
  mainNetInflow: number | null;
  isLimitUp: boolean;
  isBroken: boolean;
  consecutiveBoards: number | null;
  firstSealTime: string | null;
  lastSealTime: string | null;
  sealAmount: number | null;
  openCount: number | null;
  sealKind: "竞价封" | "盘中封" | null;
  reason: string;
  trend: number[];
};

export type MarketLeader = Omit<RankedLeader, "rank"> & {
  rank: MarketLeaderRank;
  sectorName: string | null;
};

export type SectorSnapshot = {
  rank: number;
  code: string;
  name: string;
  kind: BoardKind;
  changePercent: number | null;
  amount: number | null;
  mainNetInflow: number | null;
  upCount: number | null;
  downCount: number | null;
  memberCount: number;
  limitUpCount: number;
  brokenCount: number;
  leaders: RankedLeader[];
  trend: number[];
};

export type WatchEventKind = "封板" | "开板" | "回封" | "晋级" | "板块轮换";

export type WatchEvent = {
  id: string;
  at: string;
  kind: WatchEventKind;
  sectorName: string;
  stockName: string;
  stockCode: string;
  detail: string;
};

export type MarketSnapshot = {
  tradeDate: string;
  updatedAt: string;
  session: MarketSession;
  universe: Universe;
  sort: SectorSort;
  source: DataSource;
  indices: IndexQuote[];
  ztCount: number;
  zbCount: number;
  marketLeaders: MarketLeader[];
  sectors: SectorSnapshot[];
  error?: string;
};
