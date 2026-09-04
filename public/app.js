const $ = (id) => document.getElementById(id);

const state = {
  source: localStorage.getItem('discipline_source') || 'tongdaxin',
  timer: null,
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

async function api(path) {
  const res = await fetch(path);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function renderRules(el, bullets = []) {
  el.innerHTML = bullets.map((b) => `<li>${b}</li>`).join('');
}

function renderLowBuy(data) {
  renderRules($('lowBuyRules'), data.rule?.bullets);
  const s = data.summary || {};
  $('lowBuySummary').innerHTML = `
    <span class="tag ok">可低吸 ${s.ok ?? 0}</span>
    <span class="tag neutral">观望 ${s.neutral ?? 0}</span>
    <span class="tag chase">追高 ${s.chase ?? 0}</span>
  `;
  const body = $('lowBuyBody');
  body.innerHTML = (data.quotes || [])
    .map((q) => {
      const pos = q.dayRangePos == null ? 0 : Math.max(0, Math.min(1, q.dayRangePos));
      const statusMap = {
        ok: ['ok', '可低吸'],
        chase: ['chase', '勿追高'],
        neutral: ['neutral', '观望'],
      };
      const [sc, sl] = statusMap[q.lowBuyStatus] || statusMap.neutral;
      return `<tr>
        <td>${q.code}</td>
        <td>${q.name || '—'}</td>
        <td>${q.price ?? '—'}</td>
        <td class="${clsPct(q.changePct)}">${fmtPct(q.changePct)}</td>
        <td class="${clsPct(q.fromHighPct)}">${fmtPct(q.fromHighPct)}</td>
        <td class="${clsPct(q.fromLowPct)}">${fmtPct(q.fromLowPct)}</td>
        <td><span class="bar"><i style="width:${(pos * 100).toFixed(0)}%"></i></span>${(pos * 100).toFixed(0)}%</td>
        <td><span class="tag ${sc}">${sl}</span> <span class="meta" style="color:#5c6578">${q.lowBuyReason || ''}</span></td>
      </tr>`;
    })
    .join('');
}

function renderBoards(data) {
  renderRules($('boardRules'), data.rule?.bullets);
  const r = data.rhythm || {};
  const badge = $('rhythmBadge');
  badge.className = `status-chip ${r.code || 'watch'}`;
  badge.textContent = r.label || '—';
  const reasonEl = document.getElementById('rhythmReason');
  if (reasonEl) reasonEl.textContent = r.reason || '';

  const st = data.stats || {};
  $('boardStats').innerHTML = `
    <div class="stat"><div class="k">涨停总数</div><div class="v">${st.total ?? 0}</div></div>
    <div class="stat"><div class="k">首板</div><div class="v">${st.board1 ?? 0}</div></div>
    <div class="stat focus"><div class="k">二板 ★</div><div class="v">${st.board2 ?? 0}</div></div>
    <div class="stat focus"><div class="k">三板 ★</div><div class="v">${st.board3 ?? 0}</div></div>
  `;

  const chip = (x) => `<div class="chip"><strong>${x.name} <span class="${clsPct(x.changePct)}">${fmtPct(x.changePct)}</span></strong>
    <div class="meta">${x.code} · ${x.highDays || x.boards + '板'} · ${x.reason || ''}</div></div>`;

  $('board2List').innerHTML = (data.focus?.board2 || []).map(chip).join('') || '<div class="meta">暂无二板</div>';
  $('board3List').innerHTML = (data.focus?.board3 || []).map(chip).join('') || '<div class="meta">暂无三板</div>';
}

function renderDrawdown(data) {
  renderRules($('ddRules'), data.rule?.bullets);
  const o = data.overall || {};
  const badge = $('freezeBadge');
  badge.className = `status-chip ${o.level || 'unknown'}`;
  badge.textContent = o.label || '—';
  const reasonEl = document.getElementById('freezeReason');
  if (reasonEl) reasonEl.textContent = `${o.action || ''} — ${o.reason || ''}`;

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

async function loadSources() {
  const data = await api('/api/sources');
  const sel = $('source');
  sel.innerHTML = data.sources
    .map((s) => `<option value="${s.id}">${s.label}</option>`)
    .join('');
  sel.value = state.source;
  $('sourceNote').textContent = data.note || '';
}

async function refresh() {
  const source = $('source').value;
  state.source = source;
  localStorage.setItem('discipline_source', source);
  const codes = $('codes').value.trim();
  const q = new URLSearchParams({ source, codes });

  $('btnRefresh').disabled = true;
  try {
    const [lowBuy, boards, drawdown] = await Promise.all([
      api(`/api/discipline/low-buy?${q}`),
      api(`/api/discipline/boards?${q}`),
      api(`/api/discipline/drawdown?source=${source}`),
    ]);
    renderLowBuy(lowBuy);
    renderBoards(boards);
    renderDrawdown(drawdown);
    const used = [lowBuy.sourceLabel, boards.sourceLabel, drawdown.sourceLabel]
      .filter(Boolean)
      .filter((v, i, a) => a.indexOf(v) === i)
      .join(' / ');
    $('sourceNote').textContent = `当前：${used}`;
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
    const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    a.download = `三条纪律看板_${stamp}.png`;
    a.href = canvas.toDataURL('image/png');
    a.click();
    toast('截图已保存');
  } catch (e) {
    toast(`截图失败：${e.message}`);
  }
}

function startAuto() {
  clearInterval(state.timer);
  state.timer = setInterval(refresh, 15000);
}

$('btnRefresh').addEventListener('click', refresh);
$('btnShot').addEventListener('click', screenshot);
$('source').addEventListener('change', refresh);
$('codes').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') refresh();
});

await loadSources();
await refresh();
startAuto();
