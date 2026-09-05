const $ = (id) => document.getElementById(id);

const state = {
  source: localStorage.getItem('discipline_source') || 'tongdaxin',
  soft: localStorage.getItem('discipline_soft') || '-3',
  hard: localStorage.getItem('discipline_hard') || '-5',
  date: localStorage.getItem('discipline_date') || '',
  timer: null,
  panel: null,
  intraPeriod: '1min',
  charts: { day: null, minute: null, intra: null },
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
  if (n == null || Number.isNaN(n)) return '—';
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(digits)}%`;
}

function clsPct(n) {
  if (n == null) return '';
  return n > 0 ? 'up' : n < 0 ? 'down' : '';
}

function fmtNum(v, d = 2) {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(d) : '—';
}

async function api(path) {
  const res = await fetch(path);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
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
  };
  const [cls, text] = map[action] || map.watch;
  return `<span class="tag ${cls}">${label || text}</span>`;
}

function bindStockClicks(root) {
  root.querySelectorAll('[data-code]').forEach((el) => {
    el.addEventListener('click', () => openPanel(el.dataset.code, el.dataset.name || ''));
  });
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
  body.innerHTML = (data.quotes || [])
    .map((q) => {
      const pos = q.dayRangePos == null ? 0 : Math.max(0, Math.min(1, q.dayRangePos));
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
    .join('') || `<tr><td colspan="10" class="meta">暂无二三板可判定标的</td></tr>`;
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
    return `<button type="button" class="chip clickable" data-code="${x.code}" data-name="${x.name || ''}">
      <div class="chip-top">
        <strong>${x.name || x.code}</strong>
        <span class="${clsPct(x.changePct)}">${fmtPct(x.changePct)}</span>
        ${actionTag(action, label)}
      </div>
      <div class="meta">${x.code} · ${x.highDays || (x.boards || '') + '板'} · ${x.reason || ''} · 点击看K线/分时</div>
    </button>`;
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
}

/* ---------- Tick Stock Panel (TSP replica) ---------- */
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
  window.addEventListener('resize', () => {
    Object.values(state.charts).forEach((c) => c && c.resize());
  });
}

function renderDay(bars) {
  initCharts();
  if (!state.charts.day) return;
  const cats = (bars || []).map((b) => b.time || b.date);
  const ax = axisStyle();
  state.charts.day.setOption({
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
        itemStyle: { color: '#c62828', color0: '#1b7f4b', borderColor: '#c62828', borderColor0: '#1b7f4b' },
      },
      { type: 'bar', data: (bars || []).map((b) => b.volume), xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: '#9bb7ad' } },
    ],
  });
}

function renderMinute(minute) {
  initCharts();
  if (!state.charts.minute) return;
  const points = minute?.points || [];
  const pre = Number(minute?.pre_close || (points[0] && points[0].price) || 0);
  const times = points.map((p) => p.time);
  const ax = axisStyle();
  state.charts.minute.setOption({
    backgroundColor: 'transparent',
    animation: false,
    grid: [
      { left: 48, right: 16, top: 20, height: '58%' },
      { left: 48, right: 16, top: '78%', height: '14%' },
    ],
    xAxis: [
      { type: 'category', data: times, boundaryGap: false, ...ax, axisLabel: { show: false } },
      { type: 'category', data: times, gridIndex: 1, ...ax, axisLabel: { color: '#5c6775', fontSize: 10 } },
    ],
    yAxis: [
      { scale: true, ...ax, axisLabel: { color: '#5c6775', formatter: (v) => Number(v).toFixed(2) } },
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
  });
}

function renderIntra(bars) {
  initCharts();
  if (!state.charts.intra) return;
  const ax = axisStyle();
  state.charts.intra.setOption({
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
  });
}

function renderDepth(depth) {
  const asks = [...(depth?.asks || [])].reverse();
  const bids = depth?.bids || [];
  $('depthBox').innerHTML = `
    <div class="depth-meta">最新 ${fmtNum(depth?.price)} · 昨收 ${fmtNum(depth?.pre_close)} · ${depth?.source || ''}${depth?.tdx_host ? ' · ' + depth.tdx_host : ''}</div>
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
  $('tspSub').textContent = '加载 Tick Stock Panel…';
  const source = $('tspChartSource').value || 'tdx';
  try {
    const data = await api(`/api/panel/${code}?source=${encodeURIComponent(source)}`);
    state.panel = { ...data, code, name };
    const conn = data.tdxConnected ? 'TDX已连通' : 'TDX未连通·已回退';
    $('tspSub').textContent = `Tick Stock Panel · ${data.daySource || source} · ${conn}${data.errors?.length ? ' · 部分降级' : ''}`;
    renderDay(data.day || []);
    renderMinute(data.minute || { points: [] });
    renderIntra((state.intraPeriod === '5min' ? data.m5 : data.m1) || []);
    renderDepth(data.depth || {});
    setTimeout(() => Object.values(state.charts).forEach((c) => c && c.resize()), 40);
  } catch (err) {
    $('tspSub').textContent = `加载失败：${err.message}`;
  }
}

function closePanel() {
  $('tspMask').classList.add('hidden');
  $('tspPanel').classList.add('hidden');
}

async function loadDates() {
  const data = await api('/api/dates?limit=40');
  const sel = $('dateSelect');
  sel.innerHTML = (data.dates || [])
    .map((d) => `<option value="${d.date}">${d.label}</option>`)
    .join('');
  const preferred = state.date && [...sel.options].some((o) => o.value === state.date) ? state.date : data.default;
  sel.value = preferred;
  state.date = sel.value;
}

async function loadSources() {
  const data = await api('/api/sources');
  const sel = $('source');
  sel.innerHTML = data.sources.map((s) => `<option value="${s.id}">${s.label}</option>`).join('');
  sel.value = state.source;
  $('soft').value = state.soft;
  $('hard').value = state.hard;
  $('sourceNote').textContent = data.note || '';
}

async function refresh() {
  const source = $('source').value;
  const soft = $('soft').value;
  const hard = $('hard').value;
  const date = $('dateSelect').value;
  state.source = source;
  state.soft = soft;
  state.hard = hard;
  state.date = date;
  localStorage.setItem('discipline_source', source);
  localStorage.setItem('discipline_soft', soft);
  localStorage.setItem('discipline_hard', hard);
  localStorage.setItem('discipline_date', date);

  const q = new URLSearchParams({ source, date });
  const dq = new URLSearchParams({ source, soft, hard });

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
    $('sourceNote').textContent = `当前：${used} · 复盘 ${date}`;
    $('updatedAt').textContent = `更新 ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`;
  } catch (e) {
    toast(`刷新失败：${e.message}`);
  } finally {
    $('btnRefresh').disabled = false;
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
  state.timer = setInterval(refresh, 15000);
}

$('btnRefresh').addEventListener('click', refresh);
$('btnShot').addEventListener('click', screenshot);
$('source').addEventListener('change', refresh);
$('dateSelect').addEventListener('change', refresh);
$('soft').addEventListener('change', refresh);
$('hard').addEventListener('change', refresh);
$('tspClose').addEventListener('click', closePanel);
$('tspMask').addEventListener('click', closePanel);
$('tspShot').addEventListener('click', shotPanel);
$('tspChartSource').addEventListener('change', () => {
  if (state.panel?.code) openPanel(state.panel.code, state.panel.name || '');
});
document.querySelectorAll('.mini-tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mini-tab').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    state.intraPeriod = btn.dataset.period;
    if (state.panel) renderIntra((state.intraPeriod === '5min' ? state.panel.m5 : state.panel.m1) || []);
  });
});

await loadSources();
await loadDates();
await refresh();
startAuto();
