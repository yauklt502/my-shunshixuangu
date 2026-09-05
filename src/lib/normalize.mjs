/** Shared helpers — works in Node and Cloudflare Workers */

export function parseBoardHeight(highDays) {
  if (!highDays) return 1;
  const s = String(highDays);
  if (s.includes('首板') || s === '1') return 1;
  const m = s.match(/(\d+)\s*板/);
  if (m) return Number(m[1]);
  const n = Number(s);
  return Number.isFinite(n) ? n : 1;
}

export function toSecMarket(code) {
  const raw = String(code).trim();
  const lower = raw.toLowerCase();
  if (lower.startsWith('sh') || lower.endsWith('.sh') || lower.startsWith('1.')) {
    const c = raw.replace(/\D/g, '').padStart(6, '0').slice(-6);
    return { code: c, market: 'sh', prefix: 'sh' };
  }
  if (lower.startsWith('sz') || lower.endsWith('.sz') || lower.startsWith('0.')) {
    const c = raw.replace(/\D/g, '').padStart(6, '0').slice(-6);
    return { code: c, market: 'sz', prefix: 'sz' };
  }
  const c = raw.replace(/\D/g, '').padStart(6, '0').slice(-6);
  if (c.startsWith('6') || c.startsWith('9')) return { code: c, market: 'sh', prefix: 'sh' };
  return { code: c, market: 'sz', prefix: 'sz' };
}

export function toTencentSymbol(raw) {
  const s = String(raw).toLowerCase();
  if (s === 'sh000001' || s === '000001.sh' || s === '1.000001') return 'sh000001';
  if (s === 'sz399006' || s === '399006.sz' || s === '0.399006') return 'sz399006';
  if (s === 'sz399001' || s === '399001.sz' || s === '0.399001') return 'sz399001';
  if (s.startsWith('sh') || s.startsWith('sz')) return s.replace(/\W/g, '');
  const { code, prefix } = toSecMarket(raw);
  return `${prefix}${code}`;
}

export function pct(a, b) {
  if (!b || b === 0) return 0;
  return ((a - b) / b) * 100;
}

export function round(n, d = 2) {
  if (n == null || Number.isNaN(n)) return null;
  const p = 10 ** d;
  return Math.round(n * p) / p;
}

export function sma(values, n) {
  if (!values?.length || values.length < n) return null;
  const slice = values.slice(-n);
  return slice.reduce((a, b) => a + b, 0) / n;
}

export function makeQuote({
  code,
  name,
  price,
  open,
  prevClose,
  high,
  low,
  changePct,
  volume,
  amount,
  time,
  ma5,
}) {
  const pc = prevClose || open || price;
  const chg = changePct != null ? changePct : pct(price, pc);
  const fromHigh = high ? pct(price, high) : null;
  const fromLow = low ? pct(price, low) : null;
  const range = high && low && high !== low ? (price - low) / (high - low) : null;
  const ma5Dist = ma5 ? pct(price, ma5) : null;

  let lowBuyStatus = 'neutral';
  let lowBuyReason = '价格处于日内中位，观望';

  // 均线低吸优先：跌破/贴近 MA5 且不在追高区
  if (ma5 != null && fromHigh != null) {
    if (fromHigh >= -0.8 && chg > 5) {
      lowBuyStatus = 'chase';
      lowBuyReason = `距日内高点仅 ${Math.abs(fromHigh).toFixed(2)}%，追高区，禁止低吸`;
    } else if (ma5Dist != null && ma5Dist <= 0.6 && ma5Dist >= -3) {
      lowBuyStatus = 'ok';
      lowBuyReason = `贴近/回踩 MA5（距均线 ${ma5Dist.toFixed(2)}%），符合低吸纪律`;
    } else if (fromLow != null && (fromLow <= 1.2 || (range != null && range <= 0.28))) {
      lowBuyStatus = 'ok';
      lowBuyReason = `贴近日内低点（距低 ${Math.abs(fromLow).toFixed(2)}%），符合低吸纪律`;
    } else if (ma5Dist != null && ma5Dist > 3 && range != null && range > 0.7) {
      lowBuyStatus = 'chase';
      lowBuyReason = `远离 MA5 上方 ${ma5Dist.toFixed(2)}% 且贴近高点，勿追`;
    } else if (chg < -3 && fromHigh <= -2) {
      lowBuyStatus = 'ok';
      lowBuyReason = `回调 ${Math.abs(chg).toFixed(2)}% 且离高点较远，可评估低吸`;
    } else {
      lowBuyStatus = 'neutral';
      lowBuyReason =
        ma5Dist != null
          ? `距 MA5 ${ma5Dist.toFixed(2)}%，未到低吸位，继续等待`
          : '未贴近低点也未极端追高，继续等待';
    }
  } else if (fromHigh != null && fromLow != null) {
    if (fromHigh >= -0.8 && chg > 5) {
      lowBuyStatus = 'chase';
      lowBuyReason = `距日内高点仅 ${Math.abs(fromHigh).toFixed(2)}%，追高区，禁止低吸`;
    } else if (fromLow <= 1.2 || (range != null && range <= 0.28)) {
      lowBuyStatus = 'ok';
      lowBuyReason = `贴近日内低点（距低 ${Math.abs(fromLow).toFixed(2)}%），符合低吸纪律`;
    } else if (chg < -3 && fromHigh <= -2) {
      lowBuyStatus = 'ok';
      lowBuyReason = `回调 ${Math.abs(chg).toFixed(2)}% 且离高点较远，可评估低吸`;
    } else if (chg > 3 && range != null && range > 0.7) {
      lowBuyStatus = 'chase';
      lowBuyReason = '涨幅已大且贴近高点，勿追';
    }
  }

  return {
    code,
    name,
    price: round(price),
    open: round(open),
    prevClose: round(pc),
    high: round(high),
    low: round(low),
    changePct: round(chg),
    volume,
    amount,
    time,
    ma5: round(ma5),
    ma5DistPct: round(ma5Dist),
    fromHighPct: round(fromHigh),
    fromLowPct: round(fromLow),
    dayRangePos: range != null ? round(range, 3) : null,
    lowBuyStatus,
    lowBuyReason,
  };
}

export function drawdownFromHigh(klines) {
  if (!klines?.length) return null;
  let peak = -Infinity;
  let peakDate = null;
  for (const k of klines) {
    const h = k.high ?? k.close;
    if (h > peak) {
      peak = h;
      peakDate = k.date;
    }
  }
  const last = klines[klines.length - 1];
  return {
    peak: round(peak),
    peakDate,
    price: round(last.close),
    date: last.date,
    drawdownPct: round(pct(last.close, peak)),
  };
}

export function freezeByDrawdown(drawdownPct, soft = -3, hard = -5) {
  if (drawdownPct == null) {
    return { level: 'unknown', label: '无数据', action: '等待行情', reason: '暂无回撤数据' };
  }
  if (drawdownPct <= hard) {
    return {
      level: 'hard',
      label: '硬冻结',
      action: '禁止新开仓 / 不加仓',
      reason: `相对近期高点回撤 ${drawdownPct.toFixed(2)}% ≤ ${hard}%：只准守，不准动`,
    };
  }
  if (drawdownPct <= soft) {
    return {
      level: 'soft',
      label: '软冻结',
      action: '暂停新开仓，仅允许减仓',
      reason: `相对近期高点回撤 ${drawdownPct.toFixed(2)}% ≤ ${soft}%：回撤区，别乱动`,
    };
  }
  return {
    level: 'ok',
    label: '可操作',
    action: '可按低吸纪律交易',
    reason: `回撤 ${drawdownPct.toFixed(2)}%，未触发冻结线（软 ${soft}% / 硬 ${hard}%）`,
  };
}

const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';

export async function fetchText(url, { headers = {}, encoding = 'utf8', timeout = 12000 } = {}) {
  const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const t = ctrl ? setTimeout(() => ctrl.abort(), timeout) : null;
  try {
    const res = await fetch(url, {
      signal: ctrl?.signal,
      headers: { 'User-Agent': UA, ...headers },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = await res.arrayBuffer();
    if (encoding === 'utf8') return new TextDecoder('utf-8').decode(buf);
    // 零依赖：Node / Workers 均用内置 TextDecoder
    try {
      return new TextDecoder('gbk').decode(buf);
    } catch {
      return new TextDecoder('utf-8').decode(buf);
    }
  } finally {
    if (t) clearTimeout(t);
  }
}

export async function fetchJson(url, headers = {}) {
  const text = await fetchText(url, { headers });
  return JSON.parse(text);
}

export function todayYmd() {
  const d = new Date();
  const cn = new Date(d.getTime() + 8 * 3600 * 1000);
  return cn.toISOString().slice(0, 10).replace(/-/g, '');
}

export function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
