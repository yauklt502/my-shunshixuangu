import {
  makeQuote,
  toSecMarket,
  toTencentSymbol,
  parseBoardHeight,
  pct,
  sma,
  fetchText,
  fetchJson,
  todayYmd,
} from './normalize.mjs';

/* ========== 东方财富 ========== */
export async function eastmoneyQuotes(codes) {
  const secids = codes
    .map((c) => {
      const { code, market } = toSecMarket(c);
      return `${market === 'sh' ? 1 : 0}.${code}`;
    })
    .join(',');
  const url = `https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&secids=${secids}&fields=f12,f14,f2,f3,f4,f15,f16,f17,f18,f5,f6&ut=fa5fd1943c7b386f172d6893dbfba10b&_=${Date.now()}`;
  const data = await fetchJson(url, { Referer: 'https://quote.eastmoney.com/' });
  const list = data?.data?.diff || [];
  if (!list.length) throw new Error('东方财富行情为空（可能被出口 IP 限制）');
  return list.map((r) =>
    makeQuote({
      code: r.f12,
      name: r.f14,
      price: r.f2,
      changePct: r.f3,
      high: r.f15,
      low: r.f16,
      open: r.f17,
      prevClose: r.f18,
      volume: r.f5,
      amount: r.f6,
      time: new Date().toISOString(),
    }),
  );
}

export async function eastmoneyKline(code, lmt = 60) {
  const { code: c, market } = toSecMarket(code);
  const secid = `${market === 'sh' ? 1 : 0}.${c}`;
  const url = `https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=${secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=${lmt}&ut=fa5fd1943c7b386f172d6893dbfba10b`;
  const data = await fetchJson(url, { Referer: 'https://quote.eastmoney.com/' });
  const kl = data?.data?.klines || [];
  if (!kl.length) throw new Error('东方财富K线为空');
  return kl.map((line) => {
    const [date, open, close, high, low, volume, amount] = line.split(',');
    return {
      date,
      open: +open,
      close: +close,
      high: +high,
      low: +low,
      volume: +volume,
      amount: +amount,
    };
  });
}

export async function eastmoneyLimitUp() {
  const date = todayYmd();
  const url = `https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24410557a5&dpt=wz.ztzt&Pageindex=0&pagesize=200&sort=fbt:asc&date=${date}&_=${Date.now()}`;
  const data = await fetchJson(url, { Referer: 'https://quote.eastmoney.com/ztb/detail' });
  const pool = data?.data?.pool || [];
  if (!pool.length) throw new Error('东方财富涨停池为空');
  return pool.map((r) => {
    const boards = Number(r.lbc) || 1;
    return {
      code: r.c,
      name: r.n,
      price: r.p,
      changePct: r.zdp,
      boards,
      highDays: boards === 1 ? '首板' : `${boards}板`,
      reason: r.hybk || r.n,
      source: 'eastmoney',
    };
  });
}

/* ========== 同花顺 ========== */
function thsSymbol(code) {
  const { code: c, market } = toSecMarket(code);
  if (c === '000001' && market === 'sh') return 'hs_1A0001';
  if (c === '399006') return 'hs_399006';
  if (c === '399001') return 'hs_399001';
  return market === 'sh' ? `hs_${c}` : `sz_${c}`;
}

export async function tonghuashunQuotes(codes) {
  const out = [];
  for (const raw of codes) {
    const { code } = toSecMarket(raw);
    const sym = thsSymbol(raw);
    const url = `https://d.10jqka.com.cn/v2/realhead/${sym}/last.js?_=${Date.now()}`;
    const text = await fetchText(url, { headers: { Referer: 'https://q.10jqka.com.cn/' } });
    const m = text.match(/last\((\{[\s\S]*\})\)\s*;?\s*$/);
    if (!m) throw new Error(`同花顺解析失败 ${code}`);
    const json = JSON.parse(m[1]);
    const items = json.items || {};
    const price = +items['10'];
    const high = +items['8'];
    const low = +items['9'];
    const open = +items['7'];
    const prev = +items['6'] || open;
    out.push(
      makeQuote({
        code,
        name: String(code),
        price,
        high,
        low,
        open,
        prevClose: prev,
        changePct: pct(price, prev),
        volume: +items['13'] || 0,
        amount: +items['19'] || 0,
        time: new Date().toISOString(),
      }),
    );
  }
  return enrichNames(out);
}

export async function tonghuashunKline(code, lmt = 60) {
  const sym = thsSymbol(code);
  const url = `https://d.10jqka.com.cn/v6/line/${sym}/01/last.js?_=${Date.now()}`;
  const text = await fetchText(url, { headers: { Referer: 'https://q.10jqka.com.cn/' } });
  const m = text.match(/last\((\{[\s\S]*\})\)\s*;?\s*$/);
  if (!m) throw new Error('同花顺K线解析失败');
  const json = JSON.parse(m[1]);
  const raw = json.data || '';
  const rows = raw.split(';').filter(Boolean);
  const kl = rows.slice(-lmt).map((row) => {
    const [date, open, high, low, close, volume, amount] = row.split(',');
    return {
      date: `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`,
      open: +open,
      high: +high,
      low: +low,
      close: +close,
      volume: +volume,
      amount: +amount,
    };
  });
  if (!kl.length) throw new Error('同花顺K线为空');
  return kl;
}

export async function tonghuashunLimitUp() {
  const url =
    'https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page=1&limit=200&field=199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003&filter=HS,GEM2STAR&order_field=330324&order_type=0';
  const data = await fetchJson(url, { Referer: 'https://data.10jqka.com.cn/' });
  const info = data?.data?.info || [];
  if (!info.length) throw new Error('同花顺涨停池为空');
  return info.map((r) => ({
    code: r.code,
    name: r.name,
    price: r.latest,
    changePct: r.change_rate,
    boards: parseBoardHeight(r.high_days),
    highDays: r.high_days,
    reason: r.reason_type || r.limit_up_type,
    source: 'tonghuashun',
  }));
}

/* ========== 通达信兼容：腾讯财经 ========== */
export async function tongdaxinQuotes(codes) {
  const normalized = codes.map(toTencentSymbol);
  const url = `https://qt.gtimg.cn/q=${normalized.join(',')}&_=${Date.now()}`;
  const text = await fetchText(url, {
    headers: { Referer: 'https://finance.qq.com/' },
    encoding: 'gbk',
  });
  const quotes = [];
  for (const line of text.split('\n')) {
    if (!line.includes('=')) continue;
    const body = line.split('=')[1]?.replace(/^"|"$/g, '').replace(/";?\s*$/, '');
    if (!body) continue;
    const p = body.split('~');
    quotes.push(
      makeQuote({
        code: p[2],
        name: p[1],
        price: +p[3],
        prevClose: +p[4],
        open: +p[5],
        high: +p[33],
        low: +p[34],
        changePct: +p[32],
        volume: +p[36] || +p[6],
        amount: +p[37] || 0,
        time: p[30],
      }),
    );
  }
  if (!quotes.length) throw new Error('通达信兼容源（腾讯）行情为空');
  return quotes;
}

export async function tongdaxinKline(code, lmt = 60) {
  const symbol = toTencentSymbol(code);
  const url = `https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=${symbol}&scale=240&ma=no&datalen=${lmt}`;
  const text = await fetchText(url, { headers: { Referer: 'https://finance.sina.com.cn/' } });
  const arr = JSON.parse(text);
  if (!Array.isArray(arr) || !arr.length) throw new Error('通达信兼容K线为空');
  return arr.map((k) => ({
    date: k.day,
    open: +k.open,
    high: +k.high,
    low: +k.low,
    close: +k.close,
    volume: +k.volume,
  }));
}

export async function tongdaxinLimitUp() {
  const pool = await tonghuashunLimitUp();
  return pool.map((x) => ({ ...x, source: 'tongdaxin+ths_pool' }));
}

export async function enrichNames(quotes) {
  const need = quotes.filter((q) => !q.name || q.name === q.code);
  if (!need.length) return quotes;
  const list = need
    .map((q) => {
      const { code, prefix } = toSecMarket(q.code);
      return `${prefix}${code}`;
    })
    .join(',');
  try {
    const text = await fetchText(`https://hq.sinajs.cn/list=${list}`, {
      headers: { Referer: 'https://finance.sina.com.cn/' },
      encoding: 'gbk',
    });
    const map = {};
    for (const line of text.split('\n')) {
      const mm = line.match(/hq_str_(\w+)="([^"]*)"/);
      if (!mm || !mm[2]) continue;
      map[mm[1].slice(2)] = mm[2].split(',')[0];
    }
    return quotes.map((q) => ({ ...q, name: map[q.code] || q.name }));
  } catch {
    return quotes;
  }
}

/** Attach MA5 from kline onto quotes (best-effort) */
export async function attachMa5(quotes, klineFn) {
  const out = [];
  for (const q of quotes) {
    try {
      const kl = await klineFn(q.code, 30);
      const ma5 = sma(
        kl.map((k) => k.close),
        5,
      );
      out.push(
        makeQuote({
          ...q,
          ma5,
        }),
      );
    } catch {
      out.push(q);
    }
  }
  return out;
}

export const SOURCES = {
  eastmoney: {
    id: 'eastmoney',
    label: '东方财富',
    quotes: eastmoneyQuotes,
    kline: eastmoneyKline,
    limitUp: eastmoneyLimitUp,
  },
  tonghuashun: {
    id: 'tonghuashun',
    label: '同花顺',
    quotes: tonghuashunQuotes,
    kline: tonghuashunKline,
    limitUp: tonghuashunLimitUp,
  },
  tongdaxin: {
    id: 'tongdaxin',
    label: '通达信兼容（腾讯）',
    quotes: tongdaxinQuotes,
    kline: tongdaxinKline,
    limitUp: tongdaxinLimitUp,
  },
};
