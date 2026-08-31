import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  buildQuotesRequest,
  changePercent,
  isLimitUpPrice,
  lastTwoDayBars,
  marketFromCode,
  parseBlockDat,
  parseDayBars,
  parseQuotesBody,
  tdxPriceScale,
} from "./tdx-codec";
import { isNoiseBoard } from "./noise-boards";

describe("tdx codec", () => {
  it("maps SH / SZ / BJ / 88 boards", () => {
    assert.equal(marketFromCode("600519"), 1);
    assert.equal(marketFromCode("000001"), 0);
    assert.equal(marketFromCode("300750"), 0);
    assert.equal(marketFromCode("430001"), 2);
    assert.equal(marketFromCode("830001"), 2);
    assert.equal(marketFromCode("880302"), 1);
    assert.equal(marketFromCode("920087"), 2);
  });

  it("parses vipdoc .day last two bars", () => {
    const buf = Buffer.alloc(64);
    buf.writeInt32LE(20260828, 0);
    buf.writeInt32LE(1000, 4);
    buf.writeInt32LE(1100, 8);
    buf.writeInt32LE(900, 12);
    buf.writeInt32LE(1000, 16);
    buf.writeFloatLE(1e8, 20);
    buf.writeInt32LE(1000, 24);
    buf.writeInt32LE(20260829, 32);
    buf.writeInt32LE(1000, 36);
    buf.writeInt32LE(1200, 40);
    buf.writeInt32LE(980, 44);
    buf.writeInt32LE(1100, 48);
    buf.writeFloatLE(2e8, 52);
    buf.writeInt32LE(2000, 56);
    const bars = parseDayBars(buf);
    assert.equal(bars.length, 2);
    assert.equal(bars[0]?.close, 10);
    assert.equal(bars[1]?.close, 11);
    const last = lastTwoDayBars(buf);
    assert.equal(last.prev?.close, 10);
    assert.equal(last.last?.close, 11);
    assert.equal(tdxPriceScale(129740), 1297.4);
  });

  it("parses block_gn.dat style records", () => {
    const buf = Buffer.alloc(384 + 2 + 9 + 4 + 2800);
    buf.writeUInt16LE(1, 384);
    buf.write("新能源");
    Buffer.from("新能源\0\0\0").copy(buf, 386);
    // name is gbk, write ascii fallback
    buf.fill(0, 386, 395);
    buf.write("TESTBLK", 386, 7, "ascii");
    buf.writeUInt16LE(2, 395);
    buf.writeUInt16LE(1, 397);
    buf.write("000001", 399, 6, "ascii");
    buf.write("600519", 406, 6, "ascii");
    const blocks = parseBlockDat(new Uint8Array(buf), "concept");
    assert.equal(blocks.length, 1);
    assert.equal(blocks[0]?.name, "TESTBLK");
    assert.deepEqual(blocks[0]?.codes, ["000001", "600519"]);
  });

  it("detects 10% / 20% limit-up", () => {
    assert.equal(isLimitUpPrice("600000", "浦发银行", 11, 10), true);
    assert.equal(isLimitUpPrice("600000", "浦发银行", 10.5, 10), false);
    assert.equal(isLimitUpPrice("300001", "创业板", 12, 10), true);
    assert.equal(changePercent(11, 10), 10);
  });

  it("filters Tongdaxin statistical boards", () => {
    assert.equal(isNoiseBoard("通达信88"), true);
    assert.equal(isNoiseBoard("总市值"), true);
        assert.equal(isNoiseBoard("新能源汽车"), false);
        assert.equal(isNoiseBoard("上证50"), true);
        assert.equal(isNoiseBoard("中证A100"), true);
        assert.equal(isNoiseBoard("半导体"), false);
  });

  it("builds a quotes request of the expected size", () => {
    const pkg = buildQuotesRequest([
      { market: 1, code: "600519" },
      { market: 0, code: "000001" },
    ]);
    assert.equal(pkg.byteLength, 22 + 14);
    assert.equal(parseQuotesBody(new Uint8Array([0x01, 0x00, 0x00, 0x00])).length, 0);
  });
});
