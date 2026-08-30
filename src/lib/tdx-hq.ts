import net from "node:net";
import { inflateSync } from "node:zlib";
import {
  SETUP1,
  SETUP2,
  SETUP3,
  TDX_HQ_HOSTS,
  buildBlockChunkRequest,
  buildBlockMetaRequest,
  buildQuotesRequest,
  buildSecurityListRequest,
  marketFromCode,
  parseBlockDat,
  parseBlockMeta,
  parseQuotesBody,
  parseSecurityListBody,
  type TdxBlock,
  type TdxHqQuote,
  type TdxSecurity,
} from "./tdx-codec";

const QUOTE_BATCH = 80;

export type TdxHqSession = {
  host: string;
  port: number;
};

type Cached<T> = { value: T; exp: number };

class ByteFeed {
  private buf = Buffer.alloc(0);
  private waiters: { n: number; resolve: (b: Buffer) => void; reject: (e: Error) => void; timer: NodeJS.Timeout }[] = [];

  constructor(private sock: net.Socket) {
    sock.on("data", (chunk: Buffer) => {
      this.buf = Buffer.concat([this.buf, chunk]);
      this.flush();
    });
    sock.on("error", (err) => this.fail(err));
    sock.on("close", () => this.fail(new Error("通达信行情连接断开")));
  }

  take(n: number, timeoutMs: number): Promise<Buffer> {
    if (n <= 0) return Promise.resolve(Buffer.alloc(0));
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.waiters = this.waiters.filter((item) => item.resolve !== resolve);
        reject(new Error("通达信行情读取超时"));
      }, timeoutMs);
      this.waiters.push({ n, resolve, reject, timer });
      this.flush();
    });
  }

  private flush() {
    while (this.waiters.length && this.buf.length >= this.waiters[0]!.n) {
      const waiter = this.waiters.shift()!;
      clearTimeout(waiter.timer);
      const out = this.buf.subarray(0, waiter.n);
      this.buf = this.buf.subarray(waiter.n);
      waiter.resolve(Buffer.from(out));
    }
  }

  private fail(err: Error) {
    for (const waiter of this.waiters) {
      clearTimeout(waiter.timer);
      waiter.reject(err);
    }
    this.waiters = [];
  }
}

type LiveConn = { sock: net.Socket; feed: ByteFeed; host: string; port: number };

let live: LiveConn | null = null;
let session: TdxHqSession | null = null;
let connecting: Promise<TdxHqSession> | null = null;
const blockCache = new Map<string, Cached<TdxBlock[]>>();
const quoteCache: Cached<Map<string, TdxHqQuote>> = { value: new Map(), exp: 0 };
let nameCache: Cached<Map<string, string>> | null = null;
let listCache: Cached<{ sh: TdxSecurity[]; sz: TdxSecurity[]; bj: TdxSecurity[] }> | null = null;

async function recvPkg(feed: ByteFeed, timeoutMs = 15000): Promise<Buffer> {
  const head = await feed.take(16, timeoutMs);
  const zipsize = head.readUInt16LE(12);
  const unzipsize = head.readUInt16LE(14);
  const body = zipsize ? await feed.take(zipsize, timeoutMs) : Buffer.alloc(0);
  if (zipsize !== unzipsize) return Buffer.from(inflateSync(body));
  return body;
}

async function sendRecv(conn: LiveConn, pkg: Uint8Array, timeoutMs = 15000): Promise<Buffer> {
  conn.sock.write(pkg);
  return recvPkg(conn.feed, timeoutMs);
}

async function tryConnect(host: string, port: number): Promise<LiveConn> {
  const sock = await new Promise<net.Socket>((resolve, reject) => {
    const s = net.connect({ host, port }, () => resolve(s));
    s.setTimeout(5000);
    s.once("error", reject);
    s.once("timeout", () => {
      s.destroy();
      reject(new Error("timeout"));
    });
  });
  sock.setTimeout(0);
  const feed = new ByteFeed(sock);
  const conn = { sock, feed, host, port };
  await sendRecv(conn, SETUP1);
  await sendRecv(conn, SETUP2);
  await sendRecv(conn, SETUP3);
  const probe = await sendRecv(
    conn,
    buildQuotesRequest([
      { market: 1, code: "600519" },
      { market: 0, code: "000001" },
    ]),
  );
  const quotes = parseQuotesBody(probe);
  if (!quotes.some((item) => item.price > 0)) {
    sock.destroy();
    throw new Error("empty quotes");
  }
  return conn;
}

export async function connectTdxHq(): Promise<TdxHqSession> {
  if (live && !live.sock.destroyed && session) return session;
  if (connecting) return connecting;
  connecting = (async () => {
    let lastError: Error | null = null;
    for (const host of TDX_HQ_HOSTS) {
      try {
        const conn = await tryConnect(host.host, host.port);
        live = conn;
        conn.sock.on("close", () => {
          if (live === conn) {
            live = null;
            session = null;
          }
        });
        session = { host: host.host, port: host.port };
        return session;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
      }
    }
    throw lastError ?? new Error("通达信实时行情服务器都连不上");
  })();
  try {
    return await connecting;
  } finally {
    connecting = null;
  }
}

let queue: Promise<unknown> = Promise.resolve();

async function withConn<T>(fn: (conn: LiveConn) => Promise<T>): Promise<T> {
  const run = async () => {
    await connectTdxHq();
    if (!live || live.sock.destroyed) throw new Error("通达信行情未连接");
    try {
      return await fn(live);
    } catch (error) {
      live?.sock.destroy();
      live = null;
      session = null;
      throw error;
    }
  };
  const current = queue.then(run, run);
  queue = current.then(
    () => undefined,
    () => undefined,
  );
  return current;
}

export async function tdxHqQuotes(stocks: { market: number; code: string }[]): Promise<TdxHqQuote[]> {
  const unique = [...new Map(stocks.map((item) => [`${item.market}:${item.code}`, item])).values()];
  const out: TdxHqQuote[] = [];
  for (let i = 0; i < unique.length; i += QUOTE_BATCH) {
    const batch = unique.slice(i, i + QUOTE_BATCH);
    const body = await withConn((conn) => sendRecv(conn, buildQuotesRequest(batch)));
    out.push(...parseQuotesBody(body));
  }
  return out;
}

export async function tdxHqSecurityList(market: number): Promise<TdxSecurity[]> {
  const list: TdxSecurity[] = [];
  for (let start = 0; start < 12000; start += 1000) {
    const body = await withConn((conn) => sendRecv(conn, buildSecurityListRequest(market, start)));
    const page = parseSecurityListBody(body, market);
    list.push(...page);
    if (page.length < 1000) break;
  }
  return list;
}

export async function tdxHqDownloadBlock(
  fileName: "block_gn.dat" | "block_zs.dat" | "block.dat" | "block_fg.dat",
): Promise<TdxBlock[]> {
  const hit = blockCache.get(fileName);
  if (hit && hit.exp > Date.now()) return hit.value;
  const metaBody = await withConn((conn) => sendRecv(conn, buildBlockMetaRequest(fileName)));
  const size = parseBlockMeta(metaBody);
  if (!size) return [];
  const chunks: Buffer[] = [];
  const one = 0x7530;
  for (let start = 0; start < size; start += one) {
    const piece = await withConn((conn) => sendRecv(conn, buildBlockChunkRequest(fileName, start, size), 20000));
    const want = Math.min(one, size - start);
    const payload = piece.length > 4 ? piece.subarray(4) : piece;
    chunks.push(payload.subarray(0, Math.min(want, payload.length)));
  }
  const buffer = Buffer.concat(chunks);
  const kind = fileName.includes("gn") ? "concept" : fileName.includes("fg") ? "concept" : "industry";
  const blocks = parseBlockDat(buffer, kind);
  blockCache.set(fileName, { value: blocks, exp: Date.now() + 60 * 60 * 1000 });
  return blocks;
}

export async function tdxHqAllSecurities(): Promise<{ sh: TdxSecurity[]; sz: TdxSecurity[]; bj: TdxSecurity[] }> {
  if (listCache && listCache.exp > Date.now()) return listCache.value;
  const sh = await tdxHqSecurityList(1);
  const sz = await tdxHqSecurityList(0);
  let bj: TdxSecurity[] = [];
  try {
    bj = await tdxHqSecurityList(2);
  } catch {
    bj = [];
  }
  listCache = { value: { sh, sz, bj }, exp: Date.now() + 6 * 60 * 60 * 1000 };
  return listCache.value;
}

export async function tdxHqNameMap(): Promise<Map<string, string>> {
  if (nameCache && nameCache.exp > Date.now()) return nameCache.value;
  const { sh, sz, bj } = await tdxHqAllSecurities();
  const map = new Map<string, string>();
  for (const item of [...sh, ...sz, ...bj]) {
    if (item.name) map.set(item.code, item.name);
  }
  nameCache = { value: map, exp: Date.now() + 6 * 60 * 60 * 1000 };
  return map;
}

export async function tdxHqIndexSecurities(): Promise<TdxSecurity[]> {
  const { sh } = await tdxHqAllSecurities();
  return sh.filter((item) => item.code.startsWith("88"));
}

export async function cachedQuoteMap(codes: string[]): Promise<Map<string, TdxHqQuote>> {
  const need = codes.filter((code) => !quoteCache.value.has(code) || quoteCache.exp <= Date.now());
  if (need.length || quoteCache.exp <= Date.now()) {
    const stocks = [...new Set(codes)].map((code) => ({ market: marketFromCode(code), code }));
    const quotes = await tdxHqQuotes(stocks);
    if (quoteCache.exp <= Date.now()) quoteCache.value = new Map();
    for (const quote of quotes) quoteCache.value.set(quote.code, quote);
    quoteCache.exp = Date.now() + 8000;
  }
  return quoteCache.value;
}

export function tdxHqStatus(): TdxHqSession | null {
  return session;
}

export function closeTdxHq() {
  live?.sock.destroy();
  live = null;
  session = null;
}
