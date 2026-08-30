import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  asNumber,
  downsample,
  formatAmount,
  formatFbt,
  formatPercent,
  signedClass,
} from "./format";

describe("format", () => {
  it("parses eastmoney placeholders", () => {
    assert.equal(asNumber("-"), null);
    assert.equal(asNumber(""), null);
    assert.equal(asNumber("12.5"), 12.5);
  });

  it("formats money and percent the A-share way", () => {
    assert.equal(formatAmount(237252275), "2.37亿");
    assert.equal(formatAmount(869767473), "8.70亿");
    assert.equal(formatAmount(99896026.98), "9990万");
    assert.equal(formatPercent(10.05), "+10.05%");
    assert.equal(formatPercent(-0.11), "-0.11%");
  });

  it("pads first-seal times", () => {
    assert.equal(formatFbt(92500), "09:25:00");
    assert.equal(formatFbt(112530), "11:25:30");
    assert.equal(formatFbt(0), null);
  });

  it("maps signed colors and downsamples sparklines", () => {
    assert.equal(signedClass(1), "up");
    assert.equal(signedClass(-1), "down");
    assert.equal(signedClass(0), "flat");
    assert.deepEqual(downsample([1, 2, 3, 4, 5], 3), [1, 3, 5]);
  });
});
