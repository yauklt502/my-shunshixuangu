import type { BoardKind, DataSource, IndexQuote, MarketSession, SectorSort, Universe } from "../types";

export type SectorRole = "连板龙头" | "趋势龙头" | "中军" | "跟风" | "补涨" | "卡位";

export type RoleStock = {
  code: string;
  name: string;
  market: number;
  price: number | null;
  changePercent: number | null;
  amount: number | null;
  turnoverRate: number | null;
  isLimitUp: boolean;
  isBroken: boolean;
  consecutiveBoards: number | null;
  reason: string;
};

export type RoleGroup = {
  role: SectorRole;
  hint: string;
  stocks: RoleStock[];
};

export type LT88SectorSnapshot = {
  rank: number;
  code: string;
  name: string;
  kind: BoardKind;
  changePercent: number | null;
  amount: number | null;
  mainNetInflow: number | null;
  limitUpCount: number;
  brokenCount: number;
  memberCount: number;
  roles: RoleGroup[];
};

export type LT88Snapshot = {
  tradeDate: string;
  updatedAt: string;
  session: MarketSession;
  universe: Universe;
  sort: SectorSort;
  source: DataSource;
  indices: IndexQuote[];
  ztCount: number;
  zbCount: number;
  sectors: LT88SectorSnapshot[];
  error?: string;
};
