import { existsSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import {
  DEFAULT_TDX_ROOT,
  DEFAULT_TDX_VIPDOC,
  dayFileName,
  lastTwoDayBars,
  parseBlockDat,
  parseDayBars,
  stripMarketPrefix,
  type TdxBlock,
  type TdxDayBar,
  type TdxHqQuote,
} from "./tdx-codec";
import { beijingYmd, normalizeYmd } from "./format";

export type TdxLocalPaths = {
  vipdoc: string;
  hqCache: string;
  root: string;
};

function normalizePath(input: string): string {
  return input.replaceAll("\\", "/").replace(/\/+$/, "");
}

export function resolveTdxPaths(vipdoc = process.env.TDX_VIPDOC || DEFAULT_TDX_VIPDOC): TdxLocalPaths {
  const doc = normalizePath(vipdoc);
  const root = normalizePath(process.env.TDX_ROOT || doc.replace(/\/vipdoc$/i, "") || DEFAULT_TDX_ROOT);
  return {
    vipdoc: doc,
    root,
    hqCache: join(root, "T0002", "hq_cache"),
  };
}

export function tdxLocalAvailable(paths = resolveTdxPaths()): { ok: boolean; vipdoc: boolean; hqCache: boolean; message: string } {
  const vipdoc = existsSync(paths.vipdoc);
  const hqCache = existsSync(paths.hqCache);
  if (!vipdoc) {
    return {
      ok: false,
      vipdoc,
      hqCache,
      message: `找不到通达信本地库 ${paths.vipdoc}。请确认 E:\\new_tdx\\vipdoc 存在，或设置 TDX_VIPDOC。`,
    };
  }
  return { ok: true, vipdoc, hqCache, message: "" };
}

function readOptional(path: string): Uint8Array | null {
  try {
    if (!existsSync(path) || !statSync(path).isFile()) return null;
    return new Uint8Array(readFileSync(path));
  } catch {
    return null;
  }
}

export function readLocalBlocks(paths = resolveTdxPaths()): TdxBlock[] {
  const gn = readOptional(join(paths.hqCache, "block_gn.dat"));
  const hy = readOptional(join(paths.hqCache, "block.dat"));
  const zs = readOptional(join(paths.hqCache, "block_zs.dat"));
  const blocks: TdxBlock[] = [];
  if (gn) blocks.push(...parseBlockDat(gn, "concept"));
  if (hy) blocks.push(...parseBlockDat(hy, "industry"));
  else if (zs) blocks.push(...parseBlockDat(zs, "industry"));
  return blocks;
}

export function readDayQuote(code: string, paths = resolveTdxPaths(), dateYmd?: string): TdxHqQuote | null {
  const target = normalizeYmd(dateYmd);
  if (target && target !== beijingYmd()) {
    return readDayQuoteAtDate(code, target, paths);
  }
  const { marketDir, file } = dayFileName(code);
  const full = join(paths.vipdoc, marketDir, "lday", file);
  const buf = readOptional(full);
  if (!buf) return null;
  const { prev, last } = lastTwoDayBars(buf);
  if (!last) return null;
  return quoteFromBars(code, marketDir, prev, last);
}

function quoteFromBars(
  code: string,
  marketDir: string,
  prev: TdxDayBar | null,
  last: TdxDayBar,
): TdxHqQuote {
  return {
    market: marketDir === "sh" ? 1 : marketDir === "bj" ? 2 : 0,
    code: stripMarketPrefix(code),
    price: last.close,
    lastClose: prev?.close ?? last.close,
    open: last.open,
    high: last.high,
    low: last.low,
    amount: last.amount,
    volume: last.volume,
  };
}

export function readDayQuoteAtDate(code: string, dateYmd: string, paths = resolveTdxPaths()): TdxHqQuote | null {
  const target = Number(normalizeYmd(dateYmd));
  if (!target) return null;
  const { marketDir, file } = dayFileName(code);
  const full = join(paths.vipdoc, marketDir, "lday", file);
  const buf = readOptional(full);
  if (!buf) return null;
  const bars = parseDayBars(buf);
  const idx = bars.findIndex((bar) => bar.date === target);
  if (idx < 0) return null;
  const last = bars[idx]!;
  const prev = idx > 0 ? bars[idx - 1]! : null;
  return quoteFromBars(code, marketDir, prev, last);
}

export function readManyDayQuotes(
  codes: string[],
  paths = resolveTdxPaths(),
  dateYmd?: string,
): Map<string, TdxHqQuote> {
  const map = new Map<string, TdxHqQuote>();
  for (const code of codes) {
    const quote = readDayQuote(code, paths, dateYmd);
    if (quote) map.set(quote.code, quote);
  }
  return map;
}

export function latestDayDate(quote: TdxHqQuote, paths = resolveTdxPaths()): number | null {
  const { marketDir, file } = dayFileName(quote.code);
  const buf = readOptional(join(paths.vipdoc, marketDir, "lday", file));
  if (!buf) return null;
  const { last } = lastTwoDayBars(buf);
  return last?.date ?? null;
}

export type { TdxDayBar };
