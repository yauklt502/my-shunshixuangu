import { formatFbt } from "../format";
import { isStStock } from "../noise-boards";
import { compareLeaders, leaderReason, sealKindOf } from "../ranking";
import { eastmoneyMarket } from "../tdx-codec";
import type { StockQuote, ZbInfo, ZtInfo } from "../types";
import type { RoleGroup, RoleStock, SectorRole } from "./types";

export const ROLE_ORDER: SectorRole[] = [
  "连板龙头",
  "趋势龙头",
  "中军",
  "跟风",
  "补涨",
  "卡位",
];

export const ROLE_HINTS: Record<SectorRole, string> = {
  连板龙头: "连续涨停最多，情绪标杆，短线资金主攻方向",
  趋势龙头: "涨幅领先、趋势最强，往往走趋势而非纯连板",
  中军: "成交额大、市值大，给板块提供容量",
  跟风: "跟随龙头上涨，涨幅居中、节奏略慢",
  补涨: "低位启动接情绪，龙头高位或怕监管时出现",
  卡位: "龙头走弱、分歧加大时出现，多为炸板或高位震荡",
};

const ROLE_LIMITS: Record<SectorRole, number> = {
  连板龙头: 2,
  趋势龙头: 2,
  中军: 2,
  跟风: 3,
  补涨: 3,
  卡位: 2,
};

type Scored = {
  stock: StockQuote;
  zt: ZtInfo | undefined;
  zb: ZbInfo | undefined;
  isLimitUp: boolean;
  isBroken: boolean;
};

function toScored(
  stocks: StockQuote[],
  ztByCode: Map<string, ZtInfo>,
  zbByCode: Map<string, ZbInfo>,
): Scored[] {
  return stocks
    .filter((stock) => !isStStock(stock.name))
    .filter((stock) => stock.price !== null && stock.changePercent !== null)
    .map((stock) => ({
      stock,
      zt: ztByCode.get(stock.code),
      zb: zbByCode.get(stock.code),
      isLimitUp: Boolean(ztByCode.get(stock.code)),
      isBroken: !ztByCode.has(stock.code) && Boolean(zbByCode.get(stock.code)),
    }));
}

function toRoleStock(item: Scored): RoleStock {
  const { stock, zt, isLimitUp, isBroken } = item;
  return {
    code: stock.code,
    name: stock.name,
    market: stock.market,
    price: stock.price,
    changePercent: stock.changePercent,
    amount: stock.amount,
    turnoverRate: stock.turnoverRate,
    isLimitUp,
    isBroken,
    consecutiveBoards: zt?.consecutiveBoards ?? null,
    reason: leaderReason(item),
  };
}

function medianAmount(items: Scored[]): number {
  const amounts = items
    .map((item) => item.stock.amount ?? 0)
    .filter((value) => value > 0)
    .sort((a, b) => a - b);
  if (!amounts.length) return 0;
  const mid = Math.floor(amounts.length / 2);
  return amounts.length % 2 ? amounts[mid] : (amounts[mid - 1] + amounts[mid]) / 2;
}

function takeUnique(
  items: Scored[],
  limit: number,
  assigned: Set<string>,
): RoleStock[] {
  const picked: RoleStock[] = [];
  for (const item of items) {
    if (assigned.has(item.stock.code)) continue;
    assigned.add(item.stock.code);
    picked.push(toRoleStock(item));
    if (picked.length >= limit) break;
  }
  return picked;
}

function pick连板龙头(items: Scored[], assigned: Set<string>): RoleStock[] {
  const limitUp = items.filter((item) => item.isLimitUp).sort(compareLeaders);
  return takeUnique(limitUp, ROLE_LIMITS.连板龙头, assigned);
}

function pick中军(items: Scored[], assigned: Set<string>): RoleStock[] {
  const floor = medianAmount(items) * 0.45;
  const sorted = [...items].sort((a, b) => (b.stock.amount ?? 0) - (a.stock.amount ?? 0));
  const candidates = sorted.filter((item) => (item.stock.amount ?? 0) >= floor);
  return takeUnique(candidates, ROLE_LIMITS.中军, assigned);
}

function pick趋势龙头(items: Scored[], assigned: Set<string>): RoleStock[] {
  const candidates = items
    .filter((item) => !item.isLimitUp && !item.isBroken)
    .filter((item) => (item.stock.changePercent ?? 0) >= 4.5)
    .sort((a, b) => {
      const change =
        (b.stock.changePercent ?? Number.NEGATIVE_INFINITY) -
        (a.stock.changePercent ?? Number.NEGATIVE_INFINITY);
      if (change !== 0) return change;
      return (b.stock.amount ?? 0) - (a.stock.amount ?? 0);
    });
  return takeUnique(candidates, ROLE_LIMITS.趋势龙头, assigned);
}

function pick卡位(items: Scored[], assigned: Set<string>): RoleStock[] {
  const broken = items
    .filter((item) => item.isBroken)
    .sort((a, b) => {
      const openDiff = (b.zb?.openCount ?? 0) - (a.zb?.openCount ?? 0);
      if (openDiff !== 0) return openDiff;
      return (a.zb?.firstSealTime ?? 999999) - (b.zb?.firstSealTime ?? 999999);
    });
  const highDivergence = items
    .filter((item) => item.isLimitUp && item.zt && item.zt.openCount >= 2)
    .sort((a, b) => (b.zt?.openCount ?? 0) - (a.zt?.openCount ?? 0));
  const merged = [...broken, ...highDivergence];
  return takeUnique(merged, ROLE_LIMITS.卡位, assigned);
}

function pick跟风(items: Scored[], assigned: Set<string>): RoleStock[] {
  const candidates = items
    .filter((item) => !item.isLimitUp && !item.isBroken)
    .filter((item) => {
      const pct = item.stock.changePercent ?? 0;
      return pct >= 2.5 && pct < 9.8;
    })
    .sort((a, b) => (b.stock.changePercent ?? 0) - (a.stock.changePercent ?? 0));
  return takeUnique(candidates, ROLE_LIMITS.跟风, assigned);
}

function pick补涨(items: Scored[], assigned: Set<string>): RoleStock[] {
  const candidates = items
    .filter((item) => !item.isLimitUp && !item.isBroken)
    .filter((item) => {
      const pct = item.stock.changePercent ?? 0;
      return pct >= 0.3 && pct < 2.5;
    })
    .sort((a, b) => (b.stock.changePercent ?? 0) - (a.stock.changePercent ?? 0));
  return takeUnique(candidates, ROLE_LIMITS.补涨, assigned);
}

export function classifySectorRoles(
  stocks: StockQuote[],
  ztByCode: Map<string, ZtInfo>,
  zbByCode: Map<string, ZbInfo>,
): RoleGroup[] {
  const items = toScored(stocks, ztByCode, zbByCode);
  const assigned = new Set<string>();

  const buckets: Record<SectorRole, RoleStock[]> = {
    连板龙头: pick连板龙头(items, assigned),
    中军: pick中军(items, assigned),
    趋势龙头: pick趋势龙头(items, assigned),
    卡位: pick卡位(items, assigned),
    跟风: pick跟风(items, assigned),
    补涨: pick补涨(items, assigned),
  };

  return ROLE_ORDER.map((role) => ({
    role,
    hint: ROLE_HINTS[role],
    stocks: buckets[role],
  }));
}

export function roleReasonFallback(role: SectorRole): string {
  if (role === "连板龙头") return "暂无涨停龙头";
  if (role === "卡位") return "暂无炸板/分歧卡位";
  return "暂无符合该角色的标的";
}

/** For tests / edge cases when zt exists but stock quote missing */
export function stockQuoteFromZt(zt: ZtInfo, stockByCode: Map<string, StockQuote>): StockQuote {
  const hit = stockByCode.get(zt.code);
  if (hit) return hit;
  return {
    code: zt.code,
    name: zt.name,
    market: eastmoneyMarket(zt.code),
    price: 0,
    changePercent: 10,
    amount: zt.sealAmount,
    turnoverRate: null,
    high: null,
    low: null,
    open: null,
    speed: null,
    mainNetInflow: null,
  };
}

export function formatRoleSeal(zt: ZtInfo | undefined): string {
  if (!zt) return "";
  const time = formatFbt(zt.firstSealTime) ?? "--";
  const boards = zt.consecutiveBoards > 1 ? `${zt.consecutiveBoards}连板` : "首板";
  const kind = sealKindOf(zt);
  return `${time}${kind ?? ""} · ${boards}`;
}
