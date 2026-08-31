export type TdxMarket = 0 | 1 | 2;

export type TdxDayBar = {
  date: number;
  open: number;
  high: number;
  low: number;
  close: number;
  amount: number;
  volume: number;
};

export type TdxBlock = {
  name: string;
  kind: "concept" | "industry";
  codes: string[];
};

export type TdxHqQuote = {
  market: number;
  code: string;
  price: number;
  lastClose: number;
  open: number;
  high: number;
  low: number;
  amount: number;
  volume: number;
};

export type TdxSecurity = {
  market: number;
  code: string;
  name: string;
};

export function marketFromCode(code: string): TdxMarket {
  const six = stripMarketPrefix(code);
  if (six.startsWith("88") || six.startsWith("6")) return 1;
  if (six.startsWith("4") || six.startsWith("8") || six.startsWith("92")) return 2;
  return 0;
}

export function eastmoneyMarket(code: string): number {
  return marketFromCode(code) === 1 ? 1 : 0;
}

export function stripMarketPrefix(code: string): string {
  return code.trim().replace(/^(sh|sz|bj)/i, "").replace(/\.(SH|SZ|BJ)$/i, "");
}

export function decodeGbk(bytes: Uint8Array): string {
  return new TextDecoder("gbk").decode(bytes).replace(/\0+$/g, "").trim();
}

export function tdxPriceScale(raw: number): number {
  if (!Number.isFinite(raw) || raw === 0) return 0;
  if (Math.abs(raw) >= 1_000_000) return raw / 1000;
  return raw / 100;
}

export function parseDayBars(buffer: Uint8Array): TdxDayBar[] {
  const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  const count = Math.floor(buffer.byteLength / 32);
  const bars: TdxDayBar[] = [];
  for (let i = 0; i < count; i += 1) {
    const o = i * 32;
    bars.push({
      date: view.getInt32(o, true),
      open: tdxPriceScale(view.getInt32(o + 4, true)),
      high: tdxPriceScale(view.getInt32(o + 8, true)),
      low: tdxPriceScale(view.getInt32(o + 12, true)),
      close: tdxPriceScale(view.getInt32(o + 16, true)),
      amount: view.getFloat32(o + 20, true),
      volume: view.getInt32(o + 24, true),
    });
  }
  return bars;
}

export function lastTwoDayBars(buffer: Uint8Array): { prev: TdxDayBar | null; last: TdxDayBar | null } {
  if (buffer.byteLength < 32) return { prev: null, last: null };
  const take = buffer.byteLength >= 64 ? buffer.subarray(buffer.byteLength - 64) : buffer.subarray(buffer.byteLength - 32);
  const bars = parseDayBars(take);
  if (bars.length === 1) return { prev: null, last: bars[0]! };
  return { prev: bars[0] ?? null, last: bars[1] ?? null };
}

export function parseBlockDat(buffer: Uint8Array, kind: "concept" | "industry"): TdxBlock[] {
  if (buffer.byteLength < 386) return [];
  const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  let pos = 384;
  const num = view.getUint16(pos, true);
  pos += 2;
  const blocks: TdxBlock[] = [];
  for (let i = 0; i < num; i += 1) {
    if (pos + 13 > buffer.byteLength) break;
    const name = decodeGbk(buffer.subarray(pos, pos + 9)).replace(/[\u0000-\u0008]/g, "").trim();
    pos += 9;
    const stockCount = view.getUint16(pos, true);
    pos += 4;
    const begin = pos;
    const codes: string[] = [];
    const n = Math.min(stockCount, 400);
    for (let j = 0; j < n; j += 1) {
      if (pos + 7 > buffer.byteLength) break;
      const code = new TextDecoder("ascii")
        .decode(buffer.subarray(pos, pos + 7))
        .replace(/\0+$/g, "")
        .trim();
      pos += 7;
      if (/^\d{6}$/.test(code)) codes.push(code);
    }
    pos = begin + 2800;
    if (name && codes.length) blocks.push({ name, kind, codes });
  }
  return blocks;
}

export function getPrice(data: Uint8Array, pos: number): { value: number; pos: number } {
  let posByte = 6;
  let bdata = data[pos] ?? 0;
  let intdata = bdata & 0x3f;
  const sign = Boolean(bdata & 0x40);
  if (bdata & 0x80) {
    while (true) {
      pos += 1;
      bdata = data[pos] ?? 0;
      intdata += (bdata & 0x7f) << posByte;
      posByte += 7;
      if ((bdata & 0x80) === 0) break;
    }
  }
  pos += 1;
  if (sign) intdata = -intdata;
  return { value: intdata, pos };
}

export function getVolume(ivol: number): number {
  const logpoint = ivol >>> 24;
  const hleax = (ivol >>> 16) & 0xff;
  const lheax = (ivol >>> 8) & 0xff;
  const lleax = ivol & 0xff;
  const dwEcx = logpoint * 2 - 0x7f;
  const dwEdx = logpoint * 2 - 0x86;
  const dwEsi = logpoint * 2 - 0x8e;
  const dwEax = logpoint * 2 - 0x96;
  let dblXmm6 = 2 ** Math.abs(dwEcx);
  if (dwEcx < 0) dblXmm6 = 1 / dblXmm6;
  let dblXmm4 = 0;
  if (hleax > 0x80) {
    dblXmm4 = 2 ** dwEdx * 128 + (hleax & 0x7f) * 2 ** (dwEdx + 1);
  } else if (dwEdx >= 0) {
    dblXmm4 = 2 ** dwEdx * hleax;
  } else {
    dblXmm4 = (1 / 2 ** dwEdx) * hleax;
  }
  let dblXmm3 = 2 ** dwEsi * lheax;
  let dblXmm1 = 2 ** dwEax * lleax;
  if (hleax & 0x80) {
    dblXmm3 *= 2;
    dblXmm1 *= 2;
  }
  return dblXmm6 + dblXmm4 + dblXmm3 + dblXmm1;
}

function calPrice(base: number, diff: number): number {
  return (base + diff) / 100;
}

export function parseQuotesBody(body: Uint8Array): TdxHqQuote[] {
  if (body.byteLength < 4) return [];
  const view = new DataView(body.buffer, body.byteOffset, body.byteLength);
  let pos = 2;
  const num = view.getUint16(pos, true);
  pos += 2;
  const quotes: TdxHqQuote[] = [];
  for (let i = 0; i < num; i += 1) {
    if (pos + 9 > body.byteLength) break;
    const market = body[pos] ?? 0;
    const code = new TextDecoder("ascii").decode(body.subarray(pos + 1, pos + 7)).replace(/\0+$/g, "").trim();
    pos += 9;
    let price: number;
    ({ value: price, pos } = getPrice(body, pos));
    let lastCloseDiff: number;
    ({ value: lastCloseDiff, pos } = getPrice(body, pos));
    let openDiff: number;
    ({ value: openDiff, pos } = getPrice(body, pos));
    let highDiff: number;
    ({ value: highDiff, pos } = getPrice(body, pos));
    let lowDiff: number;
    ({ value: lowDiff, pos } = getPrice(body, pos));
    ({ pos } = getPrice(body, pos));
    ({ pos } = getPrice(body, pos));
    let volume: number;
    ({ value: volume, pos } = getPrice(body, pos));
    ({ pos } = getPrice(body, pos));
    if (pos + 4 > body.byteLength) break;
    const amount = getVolume(view.getUint32(pos, true));
    pos += 4;
    for (let skip = 0; skip < 4 + 20; skip += 1) {
      ({ pos } = getPrice(body, pos));
    }
    pos += 2;
    for (let skip = 0; skip < 4; skip += 1) {
      ({ pos } = getPrice(body, pos));
    }
    pos += 4;
    quotes.push({
      market,
      code,
      price: calPrice(price, 0),
      lastClose: calPrice(price, lastCloseDiff),
      open: calPrice(price, openDiff),
      high: calPrice(price, highDiff),
      low: calPrice(price, lowDiff),
      amount,
      volume,
    });
  }
  return quotes;
}

export function parseSecurityListBody(body: Uint8Array, market: number): TdxSecurity[] {
  if (body.byteLength < 2) return [];
  const view = new DataView(body.buffer, body.byteOffset, body.byteLength);
  const num = view.getUint16(0, true);
  let pos = 2;
  const list: TdxSecurity[] = [];
  for (let i = 0; i < num; i += 1) {
    if (pos + 29 > body.byteLength) break;
    const rec = body.subarray(pos, pos + 29);
    const code = new TextDecoder("ascii").decode(rec.subarray(0, 6)).replace(/\0+$/g, "");
    const name = decodeGbk(rec.subarray(8, 16));
    pos += 29;
    if (code) list.push({ market, code, name });
  }
  return list;
}

export function buildQuotesRequest(stocks: { market: number; code: string }[]): Uint8Array {
  const stockLen = stocks.length;
  const pkgdatalen = stockLen * 7 + 12;
  const header = Buffer.alloc(22);
  header.writeUInt16LE(0x10c, 0);
  header.writeUInt32LE(0x02006320, 2);
  header.writeUInt16LE(pkgdatalen, 6);
  header.writeUInt16LE(pkgdatalen, 8);
  header.writeUInt32LE(0x5053e, 10);
  header.writeUInt32LE(0, 14);
  header.writeUInt16LE(0, 18);
  header.writeUInt16LE(stockLen, 20);
  const parts = [header];
  for (const stock of stocks) {
    const row = Buffer.alloc(7);
    row.writeUInt8(stock.market, 0);
    row.write(stock.code.padEnd(6, "\0").slice(0, 6), 1, 6, "ascii");
    parts.push(row);
  }
  return Buffer.concat(parts);
}

export const SETUP1 = Buffer.from("0c0218930001030003000d0001", "hex");
export const SETUP2 = Buffer.from("0c0218940001030003000d0002", "hex");
export const SETUP3 = Buffer.from(
  "0c031899000120002000db0fd5d0c9ccd6a4a8af0000008fc22540130000d500c9ccbdf0d7ea00000002",
  "hex",
);

export function buildSecurityListRequest(market: number, start: number): Uint8Array {
  const pkg = Buffer.alloc(16);
  Buffer.from("0c0118640101060006005004", "hex").copy(pkg, 0);
  pkg.writeUInt16LE(market, 12);
  pkg.writeUInt16LE(start, 14);
  return pkg;
}

export function buildBlockMetaRequest(fileName: string): Uint8Array {
  const pkg = Buffer.alloc(12 + 40);
  Buffer.from("0c39186900012a002a00c502", "hex").copy(pkg, 0);
  Buffer.from(fileName).copy(pkg, 12);
  return pkg;
}

export function buildBlockChunkRequest(fileName: string, start: number, size: number): Uint8Array {
  const pkg = Buffer.alloc(12 + 8 + 100);
  Buffer.from("0c37186a00016e006e00b906", "hex").copy(pkg, 0);
  pkg.writeUInt32LE(start, 12);
  pkg.writeUInt32LE(size, 16);
  Buffer.from(fileName).copy(pkg, 20);
  return pkg;
}

export function parseBlockMeta(body: Uint8Array): number {
  if (body.byteLength < 4) return 0;
  return new DataView(body.buffer, body.byteOffset, body.byteLength).getUint32(0, true);
}

export function limitCapPercent(code: string, name: string): number {
  if (/(?:\*?ST|S\*ST)/i.test(name.replaceAll(" ", ""))) return 5;
  if (/^(300|301|688|689)/.test(code)) return 20;
  if (/^(4|8)\d{5}$/.test(code)) return 30;
  return 10;
}

export function changePercent(price: number, lastClose: number): number | null {
  if (!lastClose || !Number.isFinite(price) || !Number.isFinite(lastClose)) return null;
  return ((price - lastClose) / lastClose) * 100;
}

export function isLimitUpPrice(code: string, name: string, price: number, lastClose: number): boolean {
  const pct = changePercent(price, lastClose);
  if (pct == null) return false;
  return pct >= limitCapPercent(code, name) - 0.2;
}

export function isLimitHigh(code: string, name: string, high: number, lastClose: number): boolean {
  const pct = changePercent(high, lastClose);
  if (pct == null) return false;
  return pct >= limitCapPercent(code, name) - 0.2;
}

export function dayFileName(code: string): { marketDir: "sh" | "sz" | "bj"; file: string } {
  const six = stripMarketPrefix(code);
  const market = marketFromCode(six);
  if (market === 1) return { marketDir: "sh", file: `sh${six}.day` };
  if (market === 2) return { marketDir: "bj", file: `bj${six}.day` };
  return { marketDir: "sz", file: `sz${six}.day` };
}

export const TDX_HQ_HOSTS: { host: string; port: number }[] = [
  { host: "180.153.18.170", port: 7709 },
  { host: "115.238.56.198", port: 7709 },
  { host: "124.71.187.122", port: 7709 },
  { host: "122.51.120.217", port: 7709 },
];

export const DEFAULT_TDX_VIPDOC = "E:/new_tdx/vipdoc";
export const DEFAULT_TDX_ROOT = "E:/new_tdx";
