import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  chunkList,
  limitBreakToZb,
  limitUpToZt,
  parseThsCode,
  unwrapFuyao,
} from "./fuyao";
import { parseSnapshotQuery } from "./snapshot";

describe("fuyao helpers", () => {
  it("parses SH / SZ / BJ codes", () => {
    assert.deepEqual(parseThsCode("600519.SH"), { code: "600519", market: 1, exchange: "SH" });
    assert.deepEqual(parseThsCode("000001.sz"), { code: "000001", market: 0, exchange: "SZ" });
    assert.deepEqual(parseThsCode("430001.BJ"), { code: "430001", market: 0, exchange: "BJ" });
    assert.equal(parseThsCode("881101.TI")?.code, "881101");
    assert.equal(parseThsCode(""), null);
  });

  it("chunks batch codes", () => {
    assert.deepEqual(chunkList([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]);
    assert.deepEqual(chunkList([], 10), []);
  });

  it("unwraps Fuyao envelopes", () => {
    assert.deepEqual(unwrapFuyao({ code: 0, data: { ok: true } }), { ok: true });
    assert.throws(() => unwrapFuyao({ code: 2001 }), /密匙无效/);
    assert.throws(() => unwrapFuyao({ code: 2003 }), /权限/);
    assert.throws(() => unwrapFuyao({ code: 1001, message: "bad" }), /bad/);
  });

  it("maps limit-up and limit-break rows onto ranking fields", () => {
    const zt = limitUpToZt({
      thscode: "603986.SH",
      name: "兆易创新",
      limit_up_time: "09:34",
      continue_day_cnt: 2,
      seal_money: 1.2e8,
    });
    assert.equal(zt?.code, "603986");
    assert.equal(zt?.firstSealTime, 93400);
    assert.equal(zt?.consecutiveBoards, 2);
    assert.equal(zt?.sealAmount, 1.2e8);

    const zb = limitBreakToZb({
      thscode: "000001.SZ",
      name: "平安银行",
      open_times: 3,
      price_change_ratio_pct: 7.6,
    });
    assert.equal(zb?.code, "000001");
    assert.equal(zb?.openCount, 3);
    assert.equal(zb?.changePercent, 7.6);
  });
});

describe("snapshot query", () => {
  it("reads source, universe and sort from the query string", () => {
    const query = parseSnapshotQuery(
      new URLSearchParams("universe=concept&sort=amount&source=ths"),
    );
    assert.deepEqual(query, { universe: "concept", sort: "amount", source: "ths" });
    assert.equal(parseSnapshotQuery(new URLSearchParams("source=fuyao")).source, "ths");
    assert.equal(parseSnapshotQuery(new URLSearchParams()).source, "eastmoney");
  });
});
