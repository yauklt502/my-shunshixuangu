import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { movingAverage } from "./kline";
import { evaluateTrendChecks, rankTrendLeaders, sectorHasSync } from "./score";
import type { BoardQuote, StockQuote } from "../types";

function stock(partial: Partial<StockQuote> & Pick<StockQuote, "code" | "name">): StockQuote {
  return {
    market: 0,
    price: 10,
    changePercent: 5,
    amount: 2e8,
    turnoverRate: 6,
    high: 10.2,
    low: 9.6,
    open: 9.7,
    speed: 0,
    mainNetInflow: 0,
    ...partial,
  };
}

function board(partial: Partial<BoardQuote> & Pick<BoardQuote, "code" | "name">): BoardQuote {
  return {
    kind: "concept",
    price: null,
    changePercent: 3.2,
    amount: 5e9,
    turnoverRate: null,
    mainNetInflow: null,
    mainNetInflowPercent: null,
    upCount: 80,
    downCount: 20,
    leadName: null,
    leadCode: null,
    leadChangePercent: null,
    ...partial,
  };
}

describe("movingAverage", () => {
  it("computes simple MA", () => {
    assert.equal(movingAverage([8, 9, 10, 11, 12], 5), 10);
  });
});

describe("trend leader scoring", () => {
  it("flags sector sync when board breadth is healthy", () => {
    const members = [
      stock({ code: "000001", name: "A", changePercent: 4 }),
      stock({ code: "000002", name: "B", changePercent: 2 }),
      stock({ code: "000003", name: "C", changePercent: -1 }),
    ];
    assert.equal(sectorHasSync(board({ code: "BK1", name: "测试板块" }), members), true);
  });

  it("ranks non-limit-up trend leaders by five-angle score", () => {
    const members = [
      stock({ code: "000001", name: "趋势龙", changePercent: 6.5, amount: 3e8, turnoverRate: 8 }),
      stock({ code: "000002", name: "弱势", changePercent: 0.8, amount: 1e8, turnoverRate: 1 }),
      stock({ code: "000003", name: "涨停剔除", changePercent: 10, amount: 2e8, turnoverRate: 5 }),
    ];
    const b = board({ code: "BK1", name: "AI" });
    const closes = new Map<string, number[]>([
      ["0.000001", [9.2, 9.4, 9.6, 9.8, 10]],
      ["0.000003", [9, 9.2, 9.4, 9.6, 9.8]],
    ]);
    const zt = new Map([["000003", { code: "000003", name: "涨停剔除" } as never]]);
    const ranked = rankTrendLeaders(members, b, closes, zt, 3);
    assert.equal(ranked.length, 1);
    assert.equal(ranked[0]?.code, "000001");
    assert.ok(ranked[0]?.score >= 3);
    const checks = evaluateTrendChecks(members[0], b, members, [9.2, 9.4, 9.6, 9.8, 10]);
    assert.equal(checks.方向明确, true);
    assert.equal(checks.量价配合, true);
  });
});
