const $ = (id) => document.getElementById(id);

const state = {
  source: localStorage.getItem('td_source') || 'tongdaxin',
  soft: localStorage.getItem('td_soft') || '-3',
  hard: localStorage.getItem('td_hard') || '-5',
  date: localStorage.getItem('td_date') || '',
  codes: localStorage.getItem('td_codes') || '600519,000001,300750,002594,600900',
  timer: null,
  panel: null,
  intraPeriod: '1min',
  charts: { day: null, minute: null, intra: null },
  refreshing: false,
};

function toast(msg) {
  const el = $('toast');
  el.hidden = false;
  el.textContent = msg;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => {
    el.hidden = true;
  }, 2200);
}

function fmtPct(n, digits = 2) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  return `${v > 0 ? '+' : ''}${v.toFixed(digits)}%`;
}

function clsPct(n) {
  if (n == null || Number.isNaN(Number(n))) return '';
  const v = Number(n);
  return v > 0 ? 'up' : v < 0 ? 'down' : '';
}

function fmtNum(v, d = 2) {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(d) : '—';
}

async function api(path) {
  const res = await fetch(path);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.detail || res.statusText);
  return data;
}

function renderRules(el, bullets = []) {
  el.innerHTML = (bullets || []).map((b) => `<li>${b}</li>`).join('');
}

function actionTag(action, label) {
  const map = {
    ok: ['ok', '可买入'],
    chase: ['chase', '勿追高'],
    watch: ['neutral', '观察'],
    neutral: ['neutral', '观察'],
    hard: ['chase', '硬冻结'],
    soft: ['neutral', '软冻结'],
  };
  const [cls, text] = map[action] || map.watch;
  return `<span class="tag ${cls}">${label || text}</span>`;
}

function freezeTag(level, label) {
  const map = { hard: 'chase', soft: 'neutral', ok: 'ok', unknown: 'neutral' };
  return `<span class="tag ${map[level] || 'neutral'}">${label || level || '—'}</span>`;
}

function bindStockClicks(root) {
  root.querySelectorAll('[data-code]').forEach((el) => {
    el.addEventListener('click', (e) => {
      if (e.target.closest('[data-add]')) return;
      openPanel(el.dataset.code, el.dataset.name || '');
    });
  });
  root.querySelectorAll('[data-add]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      addToWatch(btn.dataset.add);
    });
  });
}

function addToWatch(code) {
  const c = String(code).replace(/\D/g, '').padStart(6, '0');
  const cur = $('codes')
    .value.split(/[,，\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (cur.includes(c)) {
    toast(`${c} 已在观察栏`);
    return;
  }
  cur.push(c);
  $('codes').value = cur.join(',');
  localStorage.setItem('td_codes', $('codes').value);
  toast(`已加入观察：${c}`);
  refresh();
}

function renderLowBuy(data) {
  renderRules($('lowBuyRules'), data.rule?.bullets);
  const s = data.summary || {};
  $('lowBuySummary').innerHTML = `
    <span class="tag ok">可买入 ${s.ok ?? 0}</span>
    <span class="tag neutral">观察 ${s.neutral ?? 0}</span>
    <span class="tag chase">勿追高 ${s.chase ?? 0}</span>
  `;
  const body = $('lowBuyBody');
  body.innerHTML =
    (data.quotes || [])
      .map((q) => {
        const pos = q.dayRangePos == null ? 0 : Math.max(0, Math.min(1, Number(q.dayRangePos)));
        const action = q.lowBuyStatus === 'ok' ? 'ok' : q.lowBuyStatus === 'chase' ? 'chase' : 'watch';
        const label = action === 'ok' ? '可买入' : action === 'chase' ? '勿追高' : '观察';
        return `<tr class="click-row" data-code="${q.code}" data-name="${q.name || ''}">
          <td>${q.code}</td>
          <td>${q.name || '—'}</td>
          <td>${q.price ?? '—'}</td>
          <td class="${clsPct(q.changePct)}">${fmtPct(q.changePct)}</td>
          <td>${q.ma5 ?? '—'}</td>
          <td class="${clsPct(q.ma5DistPct)}">${fmtPct(q.ma5DistPct)}</td>
          <td class="${clsPct(q.fromHighPct)}">${fmtPct(q.fromHighPct)}</td>
          <td class="${clsPct(q.fromLowPct)}">${fmtPct(q.fromLowPct)}</td>
          <td><span class="bar"><i style="width:${(pos * 100).toFixed(0)}%"></i></span>${(pos * 100).toFixed(0)}%</td>
          <td>${actionTag(action, label)} <span class="meta">${q.lowBuyReason || ''}</span></td>
        </tr>`;
      })
      .join('') || `<tr><td colspan="10" class="meta">观察栏为空</td></tr>`;
  bindStockClicks(body);
}

function renderBoards(data) {
  renderRules($('boardRules'), data.rule?.bullets);
  const r = data.rhythm || {};
  const badge = $('rhythmBadge');
  badge.className = `status-chip ${r.code || 'watch'}`;
  badge.textContent = r.label || '—';
  $('rhythmReason').textContent = r.reason || '';

  const st = data.stats || {};
  $('boardStats').innerHTML = `
    <div class="stat"><div class="k">涨停总数</div><div class="v">${st.total ?? 0}</div></div>
    <div class="stat"><div class="k">首板</div><div class="v">${st.board1 ?? 0}</div></div>
    <div class="stat focus"><div class="k">二板 ★</div><div class="v">${st.board2 ?? 0}</div></div>
    <div class="stat focus"><div class="k">三板 ★</div><div class="v">${st.board3 ?? 0}</div></div>
  `;

  const chip = (x) => {
    const action = x.action || 'watch';
    const label = x.actionLabel || (action === 'ok' ? '可买入' : action === 'chase' ? '勿追高' : '观察');
    return `<div class="chip clickable" data-code="${x.code}" data-name="${x.name || ''}">
      <div class="chip-top">
        <strong>${x.name || x.code}</strong>
        <span class="${clsPct(x.changePct)}">${fmtPct(x.changePct)}</span>
        ${actionTag(action, label)}
        <button type="button" class="chip-add" data-add="${x.code}" title="加入低吸观察">＋</button>
      </div>
      <div class="meta">${x.code} · ${x.highDays || (x.boards != null ? x.boards + '板' : '')} · ${x.reason || ''} · 点击看K线</div>
    </div>`;
  };

  $('board2List').innerHTML = (data.focus?.board2 || []).map(chip).join('') || '<div class="meta">暂无二板</div>';
  $('board3List').innerHTML = (data.focus?.board3 || []).map(chip).join('') || '<div class="meta">暂无三板</div>';
  bindStockClicks($('board2List'));
  bindStockClicks($('board3List'));
}

function renderDrawdown(data) {
  renderRules($('ddRules'), data.rule?.bullets);
  const o = data.overall || {};
  const badge = $('freezeBadge');
  badge.className = `status-chip ${o.level || 'unknown'}`;
  badge.textContent = o.label || '—';
  $('freezeReason').textContent = `${o.action || ''} — ${o.reason || ''}`;

  $('ddCards').innerHTML = (data.indices || [])
    .map((idx) => {
      const dd = idx.drawdown || {};
      const fr = idx.freeze || {};
      return `<div class="dd-card">
        <h3>${idx.name}</h3>
        <div class="dd-metric ${clsPct(dd.drawdownPct)}">${fmtPct(dd.drawdownPct)}</div>
        <p>现价 ${dd.price ?? '—'} · 近高 ${dd.peak ?? '—'}（${dd.peakDate || '—'}）</p>
        <p><strong style="color:#12141a">${fr.label || ''}</strong> — ${fr.reason || ''}</p>
        <p>数据源：${idx.sourceLabel || idx.source || ''}</p>
      </div>`;
    })
    .join('');

  const ss = data.stockSummary || {};
  $('ddStockSummary').innerHTML = `
    <span class="tag chase">硬冻结 ${ss.hard ?? 0}</span>
    <span class="tag neutral">软冻结 ${ss.soft ?? 0}</span>
    <span class="tag ok">可操作 ${ss.ok ?? 0}</span>
    <span class="tag neutral">合计 ${ss.total ?? 0}</span>
  `;

  const body = $('ddStockBody');
  body.innerHTML =
    (data.stocks || [])
      .map((s) => {
        const dd = s.drawdown || {};
        const fr = s.freeze || {};
        const board = s.boards != null ? `${s.boards}板` : s.from === 'watch' ? '观察' : '—';
        return `<tr class="click-row" data-code="${s.code}" data-name="${s.name || ''}">
          <td>${s.code}</td>
          <td>${s.name || '—'}</td>
          <td>${board}</td>
          <td class="${clsPct(s.changePct)}">${fmtPct(s.changePct)}</td>
          <td class="${clsPct(dd.drawdownPct)}">${fmtPct(dd.drawdownPct)}</td>
          <td>${dd.peak ?? '—'}<div class="meta">${dd.peakDate || ''}</div></td>
          <td>${freezeTag(fr.level, fr.label)}</td>
          <td><span class="meta">${fr.action || ''} · ${fr.reason || ''}</span></td>
        </tr>`;
      })
      .join('') || `<tr><td colspan="8" class="meta">暂无二三板/观察个股回撤数据</td></tr>`;
  bindStockClicks(body);
}

/* ---------- Tick Stock Panel（仅通达信） ---------- */
function axisStyle() {
  return {
    axisLine: { lineStyle: { color: '#c5ced8' } },
    axisLabel: { color: '#5c6775' },
    splitLine: { lineStyle: { color: '#e8eef4' } },
  };
}

function initCharts() {
  if (!window.echarts) return;
  if (!state.charts.day) state.charts.day = echarts.init($('dayChart'));
  if (!state.charts.minute) state.charts.minute = echarts.init($('minuteChart'));
  if (!state.charts.intra) state.charts.intra = echarts.init($('intraChart'));
}

function renderDay(bars) {
  initCharts();
  if (!state.charts.day) return;
  const cats = (bars || []).map((b) => b.time || b.date);
  const ax = axisStyle();
  state.charts.day.setOption(
    {
      backgroundColor: 'transparent',
      animation: false,
      grid: [
        { left: 48, right: 16, top: 18, height: '58%' },
        { left: 48, right: 16, top: '78%', height: '14%' },
      ],
      xAxis: [
        { type: 'category', data: cats, ...ax, axisLabel: { show: false } },
        { type: 'category', data: cats, gridIndex: 1, ...ax, axisLabel: { color: '#5c6775', fontSize: 10 } },
      ],
      yAxis: [
        { scale: true, ...ax },
        { scale: true, gridIndex: 1, splitNumber: 2, ...ax, axisLabel: { show: false } },
      ],
      dataZoom: [{ type: 'inside', xAxisIndex: [0, 1], start: 55, end: 100 }],
      series: [
        {
          type: 'candlestick',
          data: (bars || []).map((b) => [b.open, b.close, b.low, b.high]),
          itemStyle: { color: '#c0392b', color0: '#0f6b5c', borderColor: '#c0392b', borderColor0: '#0f6b5c' },
        },
        {
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: (bars || []).map((b) => b.volume),
          itemStyle: { color: '#9bb7ad' },
        },
      ],
    },
    true,
  );
}

function renderMinute(minute) {
  initCharts();
  if (!state.charts.minute) return;
  const points = minute?.points || [];
  const pre = Number(minute?.pre_close || minute?.preClose) || 0;
  const ax = axisStyle();
  state.charts.minute.setOption(
    {
      backgroundColor: 'transparent',
      animation: false,
      grid: [
        { left: 48, right: 16, top: 18, height: '62%' },
        { left: 48, right: 16, top: '78%', height: '14%' },
      ],
      xAxis: [
        { type: 'category', data: points.map((p) => p.time), ...ax, axisLabel: { show: false } },
        { type: 'category', data: points.map((p) => p.time), gridIndex: 1, ...ax, axisLabel: { show: false } },
      ],
      yAxis: [
        { scale: true, ...ax },
        { scale: true, gridIndex: 1, ...ax, axisLabel: { show: false } },
      ],
      series: [
        {
          type: 'line',
          data: points.map((p) => p.price),
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#1c2430' },
          areaStyle: { color: 'rgba(15,107,92,0.08)' },
          markLine: pre
            ? { symbol: 'none', label: { show: false }, data: [{ yAxis: pre }], lineStyle: { type: 'dashed', color: '#2a6f97' } }
            : undefined,
        },
        { type: 'line', data: points.map((p) => p.avg), showSymbol: false, lineStyle: { width: 1, color: '#2a6f97' } },
        { type: 'bar', data: points.map((p) => p.volume), xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: '#9bb7ad' } },
      ],
    },
    true,
  );
}

function renderIntra(bars) {
  initCharts();
  if (!state.charts.intra) return;
  const ax = axisStyle();
  state.charts.intra.setOption(
    {
      backgroundColor: 'transparent',
      animation: false,
      grid: { left: 48, right: 16, top: 18, bottom: 28 },
      xAxis: { type: 'category', data: (bars || []).map((b) => String(b.time || '').slice(5)), ...ax },
      yAxis: { scale: true, ...ax },
      series: [
        {
          type: 'line',
          data: (bars || []).map((b) => b.close),
          showSymbol: false,
          lineStyle: { width: 1.4, color: '#0f6b5c' },
          areaStyle: { color: 'rgba(15,107,92,0.1)' },
        },
      ],
    },
    true,
  );
}

function renderDepth(depth) {
  const asks = [...(depth?.asks || [])].reverse();
  const bids = depth?.bids || [];
  $('depthBox').innerHTML = `
    <div class="depth-meta">最新 ${fmtNum(depth?.price)} · 昨收 ${fmtNum(depth?.pre_close ?? depth?.preClose)} · 通达信${depth?.tdx_host || depth?.tdxHost ? ' · ' + (depth.tdx_host || depth.tdxHost) : ''}</div>
    <div class="depth-side">${
      asks.map((x, i) => `<div class="depth-row ask"><span>卖${asks.length - i}</span><span>${fmtNum(x.price)} / ${fmtNum(x.volume, 0)}</span></div>`).join('') ||
      "<div class='depth-row'>无卖档</div>"
    }</div>
    <div class="depth-side">${
      bids.map((x, i) => `<div class="depth-row bid"><span>买${i + 1}</span><span>${fmtNum(x.price)} / ${fmtNum(x.volume, 0)}</span></div>`).join('') ||
      "<div class='depth-row'>无买档</div>"
    }</div>`;
}

async function openPanel(code, name) {
  initCharts();
  $('tspMask').classList.remove('hidden');
  $('tspPanel').classList.remove('hidden');
  $('tspTitle').textContent = `${name || ''} ${code}`;
  $('tspSub').textContent = '加载通达信 Tick Stock Panel…';
  try {
    const data = await api(`/api/panel/${code}?source=tdx`);
    state.panel = { ...data, code, name };
    const host = data.tdxHost || data.tdx_host || '';
    const conn = data.tdxConnected ? 'TDX已连通' : 'TDX未连通';
    $('tspSub').textContent = `Tick Stock Panel · 通达信 TCP ${host} · ${conn}${data.errors?.length ? ' · 部分降级' : ''}`;
    renderDay(data.day || []);
    renderMinute(data.minute || { points: [] });
    renderIntra((state.intraPeriod === '5min' ? data.m5 : data.m1) || []);
    renderDepth(data.depth || {});
    setTimeout(() => Object.values(state.charts).forEach((c) => c && c.resize()), 40);
  } catch (err) {
    state.panel = { code, name };
    $('tspSub').textContent = `通达信加载失败：${err.message}`;
  }
}

function closePanel() {
  $('tspMask').classList.add('hidden');
  $('tspPanel').classList.add('hidden');
  state.panel = null;
}

async function loadDates() {
  const data = await api('/api/dates?limit=40');
  const sel = $('dateSelect');
  sel.innerHTML = (data.dates || []).map((d) => `<option value="${d.date}">${d.label}</option>`).join('');
  const preferred = state.date && [...sel.options].some((o) => o.value === state.date) ? state.date : data.default;
  sel.value = preferred || '';
  state.date = sel.value;
}

async function loadSources() {
  const data = await api('/api/sources');
  const sel = $('source');
  sel.innerHTML = (data.sources || []).map((s) => `<option value="${s.id}">${s.label}</option>`).join('');
  sel.value = state.source;
  $('soft').value = state.soft;
  $('hard').value = state.hard;
  if (state.codes) $('codes').value = state.codes;
  $('sourceNote').textContent = data.note || '';
}

async function refresh() {
  if (state.refreshing) return;
  if (state.panel && !$('tspPanel').classList.contains('hidden')) return;

  const source = $('source').value;
  const soft = $('soft').value;
  const hard = $('hard').value;
  const date = $('dateSelect').value;
  const codes = $('codes').value.trim();
  state.source = source;
  state.soft = soft;
  state.hard = hard;
  state.date = date;
  state.codes = codes;
  localStorage.setItem('td_source', source);
  localStorage.setItem('td_soft', soft);
  localStorage.setItem('td_hard', hard);
  localStorage.setItem('td_date', date);
  localStorage.setItem('td_codes', codes);

  const q = new URLSearchParams({ source, date, codes });
  const dq = new URLSearchParams({ source, soft, hard, codes });

  state.refreshing = true;
  $('btnRefresh').disabled = true;
  try {
    const [lowBuy, boards, drawdown] = await Promise.all([
      api(`/api/discipline/low-buy?${q}`),
      api(`/api/discipline/boards?${q}`),
      api(`/api/discipline/drawdown?${dq}`),
    ]);
    renderLowBuy(lowBuy);
    renderBoards(boards);
    renderDrawdown(drawdown);
    const used = [lowBuy.sourceLabel, boards.sourceLabel].filter(Boolean).filter((v, i, a) => a.indexOf(v) === i).join(' / ');
    $('sourceNote').textContent = `当前：${used || source} · 复盘 ${date || '今日'}`;
    $('updatedAt').textContent = `更新 ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`;
  } catch (e) {
    toast(`刷新失败：${e.message}`);
  } finally {
    $('btnRefresh').disabled = false;
    state.refreshing = false;
  }
}

async function screenshot() {
  if (!window.html2canvas) {
    toast('截图库未加载');
    return;
  }
  toast('正在截图…');
  try {
    const canvas = await html2canvas($('captureRoot'), {
      backgroundColor: '#ffffff',
      scale: window.devicePixelRatio > 1 ? 2 : 1,
      useCORS: true,
    });
    const a = document.createElement('a');
    a.download = `三条纪律看板_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.png`;
    a.href = canvas.toDataURL('image/png');
    a.click();
    toast('截图已保存');
  } catch (e) {
    toast(`截图失败：${e.message}`);
  }
}

async function shotPanel() {
  if (!window.html2canvas) return toast('截图库未加载');
  const canvas = await html2canvas($('tspCapture'), {
    backgroundColor: '#eef3f1',
    scale: window.devicePixelRatio > 1 ? 2 : 1,
    useCORS: true,
  });
  const a = document.createElement('a');
  a.download = `TSP_${state.panel?.code || 'panel'}_${Date.now()}.png`;
  a.href = canvas.toDataURL('image/png');
  a.click();
}

function startAuto() {
  clearInterval(state.timer);
  state.timer = setInterval(refresh, 30000);
}

$('btnRefresh').addEventListener('click', () => {
  const was = state.panel;
  if (was) state.panel = null;
  refresh().finally(() => {
    if (was && !$('tspPanel').classList.contains('hidden')) state.panel = was;
  });
});
$('btnShot').addEventListener('click', screenshot);
$('source').addEventListener('change', refresh);
$('dateSelect').addEventListener('change', refresh);
$('soft').addEventListener('change', refresh);
$('hard').addEventListener('change', refresh);
$('codes').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') refresh();
});
$('tspClose').addEventListener('click', closePanel);
$('tspMask').addEventListener('click', closePanel);
$('tspShot').addEventListener('click', shotPanel);
document.querySelectorAll('.mini-tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mini-tab').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    state.intraPeriod = btn.dataset.period;
    if (state.panel) renderIntra((state.intraPeriod === '5min' ? state.panel.m5 : state.panel.m1) || []);
  });
});
window.addEventListener('resize', () => {
  Object.values(state.charts).forEach((c) => c && c.resize());
});

await loadSources();
await loadDates();
await refresh();
startAuto();
