import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { classifySectorRoles, ROLE_ORDER } from "./roles";
import type { StockQuote, ZbInfo, ZtInfo } from "../types";

function stock(partial: Partial<StockQuote> & Pick<StockQuote, "code" | "name">): StockQuote {
  return {
    market: 0,
    price: 10,
    changePercent: 0,
    amount: 1e8,
    turnoverRate: 5,
    high: 10,
    low: 9,
    open: 9.5,
    speed: 0,
    mainNetInflow: 0,
    ...partial,
  };
}

function zt(partial: Partial<ZtInfo> & Pick<ZtInfo, "code" | "name">): ZtInfo {
  return {
    firstSealTime: 93000,
    lastSealTime: 93000,
    consecutiveBoards: 1,
    sealAmount: 5e7,
    openCount: 0,
    ztDays: 1,
    ztBoards: 1,
    industry: "测试",
    ...partial,
  };
}

describe("classifySectorRoles", () => {
  it("assigns six role buckets without duplicate codes", () => {
    const stocks = [
      stock({ code: "000001", name: "连板龙一", changePercent: 10, amount: 2e8 }),
      stock({ code: "000002", name: "连板龙二", changePercent: 10, amount: 1.5e8 }),
      stock({ code: "000003", name: "中军大票", changePercent: 6.5, amount: 9e8 }),
      stock({ code: "000004", name: "趋势先锋", changePercent: 7.8, amount: 4e8 }),
      stock({ code: "000005", name: "跟风小弟", changePercent: 5.2, amount: 2e8 }),
      stock({ code: "000006", name: "低位补涨", changePercent: 1.8, amount: 1e8 }),
      stock({ code: "000007", name: "炸板卡位", changePercent: 8.5, amount: 3e8 }),
    ];
    const ztMap = new Map<string, ZtInfo>([
      ["000001", zt({ code: "000001", name: "连板龙一", firstSealTime: 92500, consecutiveBoards: 3 })],
      ["000002", zt({ code: "000002", name: "连板龙二", firstSealTime: 93100, consecutiveBoards: 2 })],
    ]);
    const zbMap = new Map<string, ZbInfo>([
      [
        "000007",
        {
          code: "000007",
          name: "炸板卡位",
          firstSealTime: 100500,
          openCount: 2,
          changePercent: 8.5,
          industry: "测试",
        },
      ],
    ]);

    const groups = classifySectorRoles(stocks, ztMap, zbMap);
    assert.equal(groups.length, ROLE_ORDER.length);

    const codes = groups.flatMap((group) => group.stocks.map((item) => item.code));
    assert.equal(new Set(codes).size, codes.length);

    const byRole = Object.fromEntries(groups.map((group) => [group.role, group.stocks]));
    assert.deepEqual(byRole.连板龙头.map((item) => item.code), ["000001", "000002"]);
    assert.deepEqual(byRole.中军.map((item) => item.code), ["000003", "000004"]);
    assert.equal(byRole.趋势龙头[0]?.code, "000005");
    assert.equal(byRole.跟风.length, 0);
    assert.equal(byRole.补涨[0]?.code, "000006");
    assert.equal(byRole.卡位[0]?.code, "000007");
  });
});
