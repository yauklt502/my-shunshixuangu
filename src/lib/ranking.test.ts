import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { isNoiseBoard, isStStock } from "./noise-boards";
import { rankLeaders } from "./ranking";
import type { StockQuote, ZbInfo, ZtInfo } from "./types";

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

describe("filters", () => {
  it("drops statistical boards and ST names", () => {
    assert.equal(isNoiseBoard("昨日连板_含一字"), true);
    assert.equal(isNoiseBoard("历史新高"), true);
    assert.equal(isNoiseBoard("供销社概念"), false);
    assert.equal(isNoiseBoard("粮食概念"), false);
    assert.equal(isStStock("*ST海航"), true);
    assert.equal(isStStock("敦煌种业"), false);
  });
});

describe("leader ranking", () => {
  it("uses earliest limit-up as 龙一, then 龙二 龙三 by seal time and change", () => {
    const stocks = [
      stock({ code: "000001", name: "后排跟风", changePercent: 8.2, amount: 9e8 }),
      stock({ code: "000002", name: "龙二涨停", changePercent: 10, amount: 3e8 }),
      stock({ code: "000003", name: "龙一涨停", changePercent: 10, amount: 2e8 }),
      stock({ code: "000004", name: "*ST剔除", changePercent: 5, amount: 5e8 }),
    ];
    const zt = new Map<string, ZtInfo>([
      [
        "000003",
        {
          code: "000003",
          name: "龙一涨停",
          firstSealTime: 92500,
          lastSealTime: 92500,
          consecutiveBoards: 3,
          sealAmount: 1e8,
          openCount: 0,
          ztDays: 3,
          ztBoards: 3,
          industry: "农业",
        },
      ],
      [
        "000002",
        {
          code: "000002",
          name: "龙二涨停",
          firstSealTime: 93100,
          lastSealTime: 93100,
          consecutiveBoards: 1,
          sealAmount: 2e8,
          openCount: 0,
          ztDays: 1,
          ztBoards: 1,
          industry: "农业",
        },
      ],
    ]);
    const zb = new Map<string, ZbInfo>();
    const ranked = rankLeaders(stocks, zt, zb, 3);
    assert.deepEqual(
      ranked.map((item) => [item.rank, item.name]),
      [
        ["龙一", "龙一涨停"],
        ["龙二", "龙二涨停"],
        ["龙三", "后排跟风"],
      ],
    );
    assert.equal(ranked[0]?.isLimitUp, true);
    assert.equal(ranked[0]?.consecutiveBoards, 3);
    assert.match(ranked[0]?.reason ?? "", /09:25:00/);
    assert.equal(ranked[2]?.isLimitUp, false);
  });

  it("breaks same-time seals with consecutive boards then seal amount", () => {
    const stocks = [
      stock({ code: "1", name: "低封单", changePercent: 10 }),
      stock({ code: "2", name: "高连板", changePercent: 10 }),
    ];
    const zt = new Map<string, ZtInfo>([
      [
        "1",
        {
          code: "1",
          name: "低封单",
          firstSealTime: 92500,
          lastSealTime: 92500,
          consecutiveBoards: 1,
          sealAmount: 9e8,
          openCount: 0,
          ztDays: 1,
          ztBoards: 1,
          industry: null,
        },
      ],
      [
        "2",
        {
          code: "2",
          name: "高连板",
          firstSealTime: 92500,
          lastSealTime: 92500,
          consecutiveBoards: 4,
          sealAmount: 1e8,
          openCount: 0,
          ztDays: 4,
          ztBoards: 4,
          industry: null,
        },
      ],
    ]);
    const ranked = rankLeaders(stocks, zt, new Map(), 2);
    assert.equal(ranked[0]?.name, "高连板");
    assert.equal(ranked[1]?.name, "低封单");
  });

  it("treats 09:25:xx seals as 竞价封", () => {
    const stocks = [stock({ code: "1", name: "竞价龙", changePercent: 10 })];
    const zt = new Map<string, ZtInfo>([
      [
        "1",
        {
          code: "1",
          name: "竞价龙",
          firstSealTime: 92502,
          lastSealTime: 92502,
          consecutiveBoards: 4,
          sealAmount: 1e8,
          openCount: 0,
          ztDays: 4,
          ztBoards: 4,
          industry: null,
        },
      ],
    ]);
    const ranked = rankLeaders(stocks, zt, new Map(), 1);
    assert.equal(ranked[0]?.sealKind, "竞价封");
    assert.match(ranked[0]?.reason ?? "", /竞价封/);
  });
});
