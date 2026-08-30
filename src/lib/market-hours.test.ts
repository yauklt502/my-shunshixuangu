import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getMarketSession, isLiveSession, pollIntervalMs, sessionLabel } from "./market-hours";

function atShanghai(isoLocal: string): Date {
  return new Date(`${isoLocal}+08:00`);
}

describe("market hours", () => {
  it("marks weekend as closed", () => {
    const session = getMarketSession(atShanghai("2026-08-30T10:00:00"));
    assert.equal(session, "weekend");
    assert.equal(isLiveSession(session), false);
    assert.equal(sessionLabel(session), "周末休市");
  });

  it("slows Tonghuashun polling versus Eastmoney", () => {
    assert.equal(pollIntervalMs("morning", "eastmoney"), 5000);
    assert.equal(pollIntervalMs("morning", "ths"), 12000);
    assert.equal(pollIntervalMs("morning", "tdx-hq"), 10000);
    assert.equal(pollIntervalMs("closed", "tdx-local"), 45000);
    assert.equal(pollIntervalMs("closed", "ths"), 40000);
  });

  it("detects Friday morning auction and continuous trading", () => {
    assert.equal(getMarketSession(atShanghai("2026-08-28T09:20:00")), "auction");
    assert.equal(getMarketSession(atShanghai("2026-08-28T10:00:00")), "morning");
    assert.equal(getMarketSession(atShanghai("2026-08-28T12:00:00")), "lunch");
    assert.equal(getMarketSession(atShanghai("2026-08-28T14:00:00")), "afternoon");
    assert.equal(getMarketSession(atShanghai("2026-08-28T15:30:00")), "closed");
    assert.equal(isLiveSession(getMarketSession(atShanghai("2026-08-28T10:00:00"))), true);
  });
});
