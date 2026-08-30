import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { diffSnapshots } from "./events";
import type { MarketSnapshot, RankedLeader, SectorSnapshot } from "./types";

function leader(partial: Partial<RankedLeader> & Pick<RankedLeader, "code" | "name">): RankedLeader {
  return {
    rank: "龙一",
    market: 0,
    price: 10,
    changePercent: 10,
    amount: 1,
    turnoverRate: 5,
    speed: 0,
    mainNetInflow: 0,
    isLimitUp: false,
    isBroken: false,
    consecutiveBoards: 1,
    firstSealTime: "09:25:00",
    lastSealTime: "09:25:00",
    sealAmount: 1,
    openCount: 0,
    sealKind: "竞价封",
    reason: "test",
    trend: [],
    ...partial,
  };
}

function snapshot(sectors: SectorSnapshot[]): MarketSnapshot {
  return {
    tradeDate: "20260828",
    updatedAt: "2026-08-28T06:00:00.000Z",
    session: "morning",
    universe: "all",
    sort: "change",
    source: "eastmoney",
    indices: [],
    ztCount: 1,
    zbCount: 0,
    marketLeaders: [],
    sectors,
  };
}

describe("watch events", () => {
  it("emits 开板 and 回封 when limit-up state flips", () => {
    const prev = snapshot([
      {
        rank: 1,
        code: "BK1",
        name: "粮食概念",
        kind: "concept",
        changePercent: 3,
        amount: 1,
        mainNetInflow: 1,
        upCount: 10,
        downCount: 1,
        memberCount: 12,
        limitUpCount: 1,
        brokenCount: 0,
        trend: [],
        leaders: [leader({ code: "600354", name: "敦煌种业", isLimitUp: true, rank: "龙一" })],
      },
    ]);
    const opened = snapshot([
      {
        ...prev.sectors[0]!,
        leaders: [
          leader({
            code: "600354",
            name: "敦煌种业",
            isLimitUp: false,
            isBroken: true,
            rank: "龙一",
          }),
        ],
      },
    ]);
    const openEvents = diffSnapshots(prev, { ...opened, updatedAt: "t2" });
    assert.equal(openEvents[0]?.kind, "开板");

    const sealed = snapshot([
      {
        ...prev.sectors[0]!,
        leaders: [
          leader({
            code: "600354",
            name: "敦煌种业",
            isLimitUp: true,
            isBroken: false,
            rank: "龙一",
          }),
        ],
      },
    ]);
    const back = diffSnapshots(opened, { ...sealed, updatedAt: "t3" });
    assert.equal(back[0]?.kind, "回封");
  });
});
