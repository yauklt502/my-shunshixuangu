import { isStStock } from "../noise-boards";
import type { BoardQuote, StockQuote, ZtInfo } from "../types";
import { movingAverage } from "./kline";
import type { TrendCriterion, TrendLeaderStock } from "./types";
import { TREND_CRITERIA } from "./types";

function medianAmount(stocks: StockQuote[]): number {
  const amounts = stocks
    .map((stock) => stock.amount ?? 0)
    .filter((value) => value > 0)
    .sort((a, b) => a - b);
  if (!amounts.length) return 0;
  const mid = Math.floor(amounts.length / 2);
  return amounts.length % 2 ? amounts[mid] : (amounts[mid - 1] + amounts[mid]) / 2;
}

function dayPosition(stock: StockQuote): number | null {
  const { price, high, low } = stock;
  if (price === null || high === null || low === null || high <= low) return null;
  return (price - low) / (high - low);
}

function dayPullbackPct(stock: StockQuote): number | null {
  const { price, high } = stock;
  if (price === null || high === null || high <= 0) return null;
  return ((high - price) / high) * 100;
}

export function sectorHasSync(board: BoardQuote, members: StockQuote[]): boolean {
  const up = board.upCount ?? 0;
  const down = board.downCount ?? 0;
  const total = up + down;
  const boardStrong = (board.changePercent ?? 0) >= 0.8;
  const breadth = total > 0 ? up / total >= 0.45 : false;
  const greenRatio =
    members.length > 0
      ? members.filter((item) => (item.changePercent ?? 0) > 0).length / members.length
      : 0;
  return boardStrong && breadth && greenRatio >= 0.35;
}

export function evaluateTrendChecks(
  stock: StockQuote,
  board: BoardQuote,
  members: StockQuote[],
  priorCloses: number[],
): Record<TrendCriterion, boolean> {
  const price = stock.price;
  const change = stock.changePercent ?? 0;
  const open = stock.open;
  const position = dayPosition(stock);
  const pullback = dayPullbackPct(stock);

  const history = priorCloses.length ? priorCloses : [];
  const ma5 = price !== null ? movingAverage([...history, price], 5) : movingAverage(history, 5);

  const 方向明确 =
    change >= 2.5 &&
    change < 9.8 &&
    price !== null &&
    open !== null &&
    price >= open &&
    position !== null &&
    position >= 0.6;

  const 均线支撑 =
    price !== null &&
    ma5 !== null &&
    ma5 > 0 &&
    price >= ma5 * 0.992;

  const floor = medianAmount(members) * 0.75;
  const 量价配合 =
    change > 0 &&
    (stock.turnoverRate ?? 0) >= 2.5 &&
    (stock.amount ?? 0) >= floor;

  const 回调浅 = pullback !== null && pullback <= 4.5;

  const 板块有配合 = sectorHasSync(board, members);

  return { 方向明确, 均线支撑, 量价配合, 回调浅, 板块有配合 };
}

function buildReason(checks: Record<TrendCriterion, boolean>, ma5: number | null, pullback: number | null): string {
  const hits = TREND_CRITERIA.filter((key) => checks[key]);
  const parts: string[] = [];
  if (hits.length) parts.push(`符合 ${hits.length}/5：${hits.join("、")}`);
  if (ma5 !== null) parts.push(`MA5≈${ma5.toFixed(2)}`);
  if (pullback !== null) parts.push(`日内回落 ${pullback.toFixed(1)}%`);
  return parts.join(" · ") || "趋势特征偏弱";
}

export function scoreTrendLeader(
  stock: StockQuote,
  board: BoardQuote,
  members: StockQuote[],
  priorCloses: number[],
  ztByCode: Map<string, ZtInfo>,
): TrendLeaderStock | null {
  if (isStStock(stock.name)) return null;
  if (ztByCode.has(stock.code)) return null;
  if (stock.price === null || stock.changePercent === null) return null;
  if (stock.changePercent < 1.5 || stock.changePercent >= 9.9) return null;

  const checks = evaluateTrendChecks(stock, board, members, priorCloses);
  const score = TREND_CRITERIA.filter((key) => checks[key]).length;
  if (score < 3) return null;

  const history = priorCloses.length ? priorCloses : [];
  const ma5 =
    stock.price !== null
      ? movingAverage([...history, stock.price], 5)
      : movingAverage(history, 5);
  const pullback = dayPullbackPct(stock);

  return {
    code: stock.code,
    name: stock.name,
    market: stock.market,
    price: stock.price,
    changePercent: stock.changePercent,
    amount: stock.amount,
    turnoverRate: stock.turnoverRate,
    score,
    checks,
    ma5,
    dayPullbackPct: pullback,
    reason: buildReason(checks, ma5, pullback),
  };
}

export function rankTrendLeaders(
  stocks: StockQuote[],
  board: BoardQuote,
  closesByCode: Map<string, number[]>,
  ztByCode: Map<string, ZtInfo>,
  limit = 5,
): TrendLeaderStock[] {
  const scored = stocks
    .map((stock) => {
      const closes = closesByCode.get(`${stock.market}.${stock.code}`) ?? [];
      return scoreTrendLeader(stock, board, stocks, closes, ztByCode);
    })
    .filter((item): item is TrendLeaderStock => Boolean(item));

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return (b.changePercent ?? 0) - (a.changePercent ?? 0);
  });

  return scored.slice(0, limit);
}
