/** Parse 「N天M板」 / 「首板」 → board height number */
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

export function pct(a, b) {
  if (!b || b === 0) return 0;
  return ((a - b) / b) * 100;
}

export function round(n, d = 2) {
  if (n == null || Number.isNaN(n)) return null;
  const p = 10 ** d;
  return Math.round(n * p) / p;
}

/** Unified quote shape */
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
}) {
  const pc = prevClose || open || price;
  const chg = changePct != null ? changePct : pct(price, pc);
  const fromHigh = high ? pct(price, high) : null;
  const fromLow = low ? pct(price, low) : null;
  const range = high && low && high !== low ? (price - low) / (high - low) : null;

  // 低吸纪律：靠近日内低点 / 远离高点 / 不在追高区
  let lowBuyStatus = 'neutral';
  let lowBuyReason = '价格处于日内中位，观望';
  if (fromHigh != null && fromLow != null) {
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
    } else {
      lowBuyStatus = 'neutral';
      lowBuyReason = '未贴近低点也未极端追高，继续等待';
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
    fromHighPct: round(fromHigh),
    fromLowPct: round(fromLow),
    dayRangePos: range != null ? round(range, 3) : null,
    lowBuyStatus,
    lowBuyReason,
  };
}

export function drawdownFromHigh(klines) {
  // klines: [{date, close, high}] ascending
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
  const price = last.close;
  const dd = pct(price, peak);
  return {
    peak: round(peak),
    peakDate,
    price: round(price),
    date: last.date,
    drawdownPct: round(dd),
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
