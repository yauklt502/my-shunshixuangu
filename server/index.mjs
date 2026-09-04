import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { SOURCES } from './sources/adapters.mjs';
import {
  drawdownFromHigh,
  freezeByDrawdown,
  parseBoardHeight,
} from './sources/normalize.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const app = express();
const PORT = process.env.PORT || 5177;

const DEFAULT_WATCH = ['600519', '000001', '300750', '002594', '600900'];
const INDEX_CODES = {
  sh: 'sh000001',
  cyb: 'sz399006',
};

app.use(express.json());
app.use(express.static(path.join(root, 'public')));

function pickSource(req) {
  const id = String(req.query.source || req.body?.source || 'tongdaxin').toLowerCase();
  const src = SOURCES[id] || SOURCES.tongdaxin;
  return src;
}

function parseCodes(q) {
  if (!q) return DEFAULT_WATCH;
  return String(q)
    .split(/[,，\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

async function withFallback(primaryId, method, args) {
  const order = [primaryId, 'tongdaxin', 'tonghuashun', 'eastmoney'].filter(
    (v, i, a) => a.indexOf(v) === i,
  );
  const errors = [];
  for (const id of order) {
    const src = SOURCES[id];
    if (!src?.[method]) continue;
    try {
      const data = await src[method](...args);
      return { data, used: id, label: src.label, errors };
    } catch (e) {
      errors.push({ source: id, message: e.message || String(e) });
    }
  }
  throw new Error(errors.map((e) => `${e.source}: ${e.message}`).join(' | ') || '全部数据源失败');
}

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, sources: Object.keys(SOURCES) });
});

app.get('/api/sources', (_req, res) => {
  res.json({
    sources: Object.values(SOURCES).map((s) => ({ id: s.id, label: s.label })),
    note: '通达信项使用腾讯财经免费行情（与通达信客户端同源公开源）；涨停池在东方财富不可用时自动回退同花顺。',
  });
});

app.get('/api/quotes', async (req, res) => {
  try {
    const src = pickSource(req);
    const codes = parseCodes(req.query.codes);
    const { data, used, label, errors } = await withFallback(src.id, 'quotes', [codes]);
    res.json({ source: used, sourceLabel: label, quotes: data, fallbackErrors: errors });
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.get('/api/discipline/low-buy', async (req, res) => {
  try {
    const src = pickSource(req);
    const codes = parseCodes(req.query.codes);
    const { data, used, label, errors } = await withFallback(src.id, 'quotes', [codes]);
    const summary = {
      ok: data.filter((q) => q.lowBuyStatus === 'ok').length,
      chase: data.filter((q) => q.lowBuyStatus === 'chase').length,
      neutral: data.filter((q) => q.lowBuyStatus === 'neutral').length,
    };
    res.json({
      source: used,
      sourceLabel: label,
      rule: {
        title: '低吸纪律',
        bullets: [
          '只买贴近日内低点或明显回调的位置，不买贴近日内高点的票',
          '涨幅已大且价格在日内高位区间 → 追高区，禁止低吸',
          '距低点 ≤1.2% 或处在日内下方 28% 区间 → 符合低吸',
          '一句话：低吸是买「便宜的相对位置」，不是买「便宜的名字」',
        ],
      },
      summary,
      quotes: data,
      fallbackErrors: errors,
      updatedAt: new Date().toISOString(),
    });
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.get('/api/discipline/boards', async (req, res) => {
  try {
    const src = pickSource(req);
    const { data, used, label, errors } = await withFallback(src.id, 'limitUp', []);
    const enriched = data.map((x) => ({
      ...x,
      boards: x.boards || parseBoardHeight(x.highDays),
    }));
    const board1 = enriched.filter((x) => x.boards === 1);
    const board2 = enriched.filter((x) => x.boards === 2);
    const board3 = enriched.filter((x) => x.boards === 3);
    const board4p = enriched.filter((x) => x.boards >= 4);

    // 节奏判定
    let rhythm = 'watch';
    let rhythmLabel = '观望';
    let rhythmReason = '';
    const total = enriched.length || 1;
    const focus = board2.length + board3.length;
    if (board2.length >= 3 && board3.length >= 1) {
      rhythm = 'healthy';
      rhythmLabel = '二三板活跃';
      rhythmReason = `二板 ${board2.length} / 三板 ${board3.length}，梯队成形，短线情绪健康，重点盯二三板接力`;
    } else if (board2.length >= 2 && board3.length === 0) {
      rhythm = 'early';
      rhythmLabel = '二板试错期';
      rhythmReason = `二板 ${board2.length}、三板 0，情绪偏早，可观察二板质量，勿盲目抬高预期`;
    } else if (board1.length / total > 0.75 && focus <= 1) {
      rhythm = 'weak';
      rhythmLabel = '高度不足';
      rhythmReason = '首板占比过高、二三板稀缺，亏钱效应易扩散，节奏偏弱';
    } else if (board4p.length >= 2 && board2.length <= 1) {
      rhythm = 'fragile';
      rhythmLabel = '高位独苗';
      rhythmReason = '高位板多但二三板断层，龙头容易核，回撤时更要少动';
    } else {
      rhythm = 'mixed';
      rhythmLabel = '结构一般';
      rhythmReason = `二板 ${board2.length} / 三板 ${board3.length} / 首板 ${board1.length}，按个股质量选，不追情绪`;
    }

    res.json({
      source: used,
      sourceLabel: label,
      rule: {
        title: '二三板节奏',
        bullets: [
          '连板关键观察点在二板、三板，不是一板盲冲',
          '二板≥3 且三板≥1 → 梯队健康，可做情绪接力',
          '只有首板、高度上不去 → 节奏弱，降低仓位与频率',
          '高位独苗（4板以上多、二三板断层）→ 脆弱，防核按钮',
        ],
      },
      rhythm: { code: rhythm, label: rhythmLabel, reason: rhythmReason },
      stats: {
        total: enriched.length,
        board1: board1.length,
        board2: board2.length,
        board3: board3.length,
        board4p: board4p.length,
      },
      focus: {
        board2: board2.slice(0, 20),
        board3: board3.slice(0, 20),
      },
      all: enriched,
      fallbackErrors: errors,
      updatedAt: new Date().toISOString(),
    });
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.get('/api/discipline/drawdown', async (req, res) => {
  try {
    const src = pickSource(req);
    const soft = Number(req.query.soft ?? -3);
    const hard = Number(req.query.hard ?? -5);
    const days = Number(req.query.days ?? 20);

    const targets = [
      { id: 'sh', name: '上证指数', code: INDEX_CODES.sh },
      { id: 'cyb', name: '创业板指', code: INDEX_CODES.cyb },
    ];

    const results = [];
    const errors = [];
    for (const t of targets) {
      try {
        const { data: kl, used, label } = await withFallback(src.id, 'kline', [t.code, days]);
        const dd = drawdownFromHigh(kl);
        const freeze = freezeByDrawdown(dd?.drawdownPct, soft, hard);
        results.push({
          ...t,
          source: used,
          sourceLabel: label,
          drawdown: dd,
          freeze,
          recent: kl.slice(-8),
        });
      } catch (e) {
        errors.push({ target: t.id, message: e.message });
      }
    }

    // overall: take the worse freeze level
    const rank = { hard: 3, soft: 2, ok: 1, unknown: 0 };
    const worst = results.reduce(
      (a, b) => (rank[b.freeze.level] > rank[a.freeze.level] ? b : a),
      results[0] || { freeze: { level: 'unknown', label: '无数据', action: '等待', reason: '' } },
    );

    res.json({
      source: src.id,
      sourceLabel: src.label,
      rule: {
        title: '回撤时别乱动',
        bullets: [
          `相对近 ${days} 日高点回撤 ≤ ${soft}%：软冻结——暂停新开仓`,
          `回撤 ≤ ${hard}%：硬冻结——禁止新开仓/加仓，只准防守`,
          '回撤区最常见亏法：忍不住「补仓摊薄」和「换股乱动」',
          '真实体现：看指数离阶段高点多远，再决定动不动手',
        ],
      },
      thresholds: { soft, hard, days },
      overall: worst.freeze,
      indices: results,
      fallbackErrors: errors,
      updatedAt: new Date().toISOString(),
    });
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.get('/api/discipline/overview', async (req, res) => {
  const src = pickSource(req);
  const codes = parseCodes(req.query.codes);
  const base = `http://127.0.0.1:${PORT}`;
  const q = new URLSearchParams({ source: src.id, codes: codes.join(',') });
  try {
    const [lowBuy, boards, drawdown] = await Promise.all([
      fetch(`${base}/api/discipline/low-buy?${q}`).then((r) => r.json()),
      fetch(`${base}/api/discipline/boards?${q}`).then((r) => r.json()),
      fetch(`${base}/api/discipline/drawdown?source=${src.id}`).then((r) => r.json()),
    ]);
    res.json({
      source: src.id,
      sourceLabel: src.label,
      lowBuy,
      boards,
      drawdown,
      updatedAt: new Date().toISOString(),
    });
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.get('*', (_req, res) => {
  res.sendFile(path.join(root, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Three-discipline dashboard http://127.0.0.1:${PORT}`);
});
