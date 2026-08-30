import { formatFbt } from "./format";
import { isStStock } from "./noise-boards";
import type {
  LeaderRank,
  RankedLeader,
  StockQuote,
  ZbInfo,
  ZtInfo,
} from "./types";

const RANKS: LeaderRank[] = ["龙一", "龙二", "龙三"];

type Scored = {
  stock: StockQuote;
  zt: ZtInfo | undefined;
  zb: ZbInfo | undefined;
  isLimitUp: boolean;
  isBroken: boolean;
};

export function compareLeaders(a: Scored, b: Scored): number {
  if (a.isLimitUp !== b.isLimitUp) return a.isLimitUp ? -1 : 1;

  if (a.isLimitUp && b.isLimitUp && a.zt && b.zt) {
    if (a.zt.firstSealTime !== b.zt.firstSealTime) {
      return a.zt.firstSealTime - b.zt.firstSealTime;
    }
    if (a.zt.consecutiveBoards !== b.zt.consecutiveBoards) {
      return b.zt.consecutiveBoards - a.zt.consecutiveBoards;
    }
    return (b.zt.sealAmount ?? 0) - (a.zt.sealAmount ?? 0);
  }

  const change =
    (b.stock.changePercent ?? Number.NEGATIVE_INFINITY) -
    (a.stock.changePercent ?? Number.NEGATIVE_INFINITY);
  if (change !== 0) return change;
  return (b.stock.amount ?? 0) - (a.stock.amount ?? 0);
}

export function sealKindOf(zt: ZtInfo | undefined): RankedLeader["sealKind"] {
  if (!zt) return null;
  if (zt.firstSealTime <= 92559) return "竞价封";
  return "盘中封";
}

export function leaderReason(item: Scored): string {
  if (item.isLimitUp && item.zt) {
    const time = formatFbt(item.zt.firstSealTime) ?? "--";
    const boards =
      item.zt.consecutiveBoards > 1 ? `${item.zt.consecutiveBoards}连板` : "首板";
    const kind = sealKindOf(item.zt);
    const open =
      item.zt.openCount > 0 ? ` · 开板${item.zt.openCount}次` : " · 未开板";
    return `${time}${kind ?? ""} · ${boards}${open}`;
  }
  if (item.isBroken && item.zb) {
    const time = formatFbt(item.zb.firstSealTime) ?? "--";
    return `${time}曾封 · 炸板${item.zb.openCount || 1}次`;
  }
  const pct = item.stock.changePercent;
  if (pct !== null && pct !== undefined) {
    return `板块内涨幅 ${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
  }
  return "板块内排序";
}

export function rankLeaders(
  stocks: StockQuote[],
  ztByCode: Map<string, ZtInfo>,
  zbByCode: Map<string, ZbInfo>,
  limit = 3,
): RankedLeader[] {
  const scored: Scored[] = stocks
    .filter((stock) => !isStStock(stock.name))
    .filter((stock) => stock.price !== null && stock.changePercent !== null)
    .map((stock) => {
      const zt = ztByCode.get(stock.code);
      const zb = zbByCode.get(stock.code);
      return {
        stock,
        zt,
        zb,
        isLimitUp: Boolean(zt),
        isBroken: !zt && Boolean(zb),
      };
    });

  scored.sort(compareLeaders);

  return scored.slice(0, limit).map((item, index) => {
    const { stock, zt, zb, isLimitUp, isBroken } = item;
    return {
      rank: RANKS[index] ?? "龙三",
      code: stock.code,
      name: stock.name,
      market: stock.market,
      price: stock.price,
      changePercent: stock.changePercent,
      amount: stock.amount,
      turnoverRate: stock.turnoverRate,
      speed: stock.speed,
      mainNetInflow: stock.mainNetInflow,
      isLimitUp,
      isBroken,
      consecutiveBoards: zt?.consecutiveBoards ?? null,
      firstSealTime: formatFbt(zt?.firstSealTime ?? zb?.firstSealTime ?? null),
      lastSealTime: formatFbt(zt?.lastSealTime ?? null),
      sealAmount: zt?.sealAmount ?? null,
      openCount: zt?.openCount ?? zb?.openCount ?? null,
      sealKind: sealKindOf(zt),
      reason: leaderReason(item),
      trend: [],
    };
  });
}
