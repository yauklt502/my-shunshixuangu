(() => {
  const state = {
    date: "",
    source: "eastmoney",
    panel: null,
    intraPeriod: "1min",
    charts: { day: null, minute: null, intra: null },
  };
  const $ = (id) => document.getElementById(id);
  const fmtPct = (v) => {
    const n = Number(v || 0);
    return `<span class="${n >= 0 ? "up" : "down"}">${n >= 0 ? "+" : ""}${n.toFixed(2)}%</span>`;
  };
  const fmtNum = (v, d = 2) => {
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(d) : "—";
  };
  async function api(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(`${path} HTTP ${r.status}`);
    return r.json();
  }
  function axis() {
    return {
      axisLine: { lineStyle: { color: "#c5ced8" } },
      axisLabel: { color: "#5c6775" },
      splitLine: { lineStyle: { color: "#e8eef4" } },
    };
  }
  function initCharts() {
    state.charts.day = echarts.init($("dayChart"));
    state.charts.minute = echarts.init($("minuteChart"));
    state.charts.intra = echarts.init($("intraChart"));
    window.addEventListener("resize", () => Object.values(state.charts).forEach((c) => c && c.resize()));
  }
  async function loadDates() {
    const data = await api("/api/dates?limit=40");
    $("dateSelect").innerHTML = (data.dates || []).map((d) => `<option value="${d.date}">${d.label}</option>`).join("");
    state.date = data.default || data.today;
    $("dateSelect").value = state.date;
  }
  async function loadSources() {
    try {
      const data = await api("/api/sources");
      if (data.sources?.length) {
        $("sourceSelect").innerHTML = data.sources.map((s) => `<option value="${s.id}">${s.name}</option>`).join("");
        state.source = data.default || data.sources[0].id;
        $("sourceSelect").value = state.source;
      }
    } catch (_) {}
  }
  function bindRows(tbody) {
    tbody.querySelectorAll("tr[data-code]").forEach((tr) => {
      tr.onclick = () => openPanel(tr.dataset.code, tr.dataset.name);
    });
  }
  function renderHot(boards) {
    $("hotBoards").innerHTML = boards?.length
      ? boards.slice(0, 12).map((b) => `<div class="chip">${b.name || b.code}<strong>${fmtNum(b.change_pct)}%</strong></div>`).join("")
      : `<div class="chip">暂无足够强的启动赛道</div>`;
  }
  function renderTables(data) {
    $("leaderBody").innerHTML =
      (data.leaders || [])
        .map(
          (x) => `<tr data-code="${x.code}" data-name="${x.name || ""}">
          <td>${x.code}</td><td>${x.name || ""}</td><td>${x.industry || "—"}</td>
          <td>${fmtNum(x.price)}</td><td>${fmtPct(x.change_pct)}</td>
          <td>${x.boards ?? "—"}</td><td>${x.open_count ?? "—"}</td>
          <td>${fmtNum(x.score_xian, 1)}</td><td>${fmtNum(x.score_bi, 1)}</td><td>${fmtNum(x.score_du, 1)}</td>
          <td><strong>${fmtNum(x.score, 1)}</strong></td>
          <td class="notes">${(x.notes || []).slice(0, 3).join(" · ")}</td></tr>`
        )
        .join("") || `<tr><td colspan="12">暂无核心领涨</td></tr>`;
    $("anchorBody").innerHTML =
      (data.anchors || [])
        .map(
          (x) => `<tr data-code="${x.code}" data-name="${x.name || ""}">
          <td>${x.code}</td><td>${x.name || ""}</td><td>${x.boards ?? "—"}</td>
          <td>${x.industry || "—"}</td><td>${fmtNum(x.score, 1)}</td></tr>`
        )
        .join("") || `<tr><td colspan="5">无</td></tr>`;
    $("watchBody").innerHTML =
      (data.watch || [])
        .map(
          (x) => `<tr data-code="${x.code}" data-name="${x.name || ""}">
          <td>${x.code}</td><td>${x.name || ""}</td><td>${fmtPct(x.change_pct)}</td>
          <td>${x.boards ?? "—"}</td><td>${fmtNum(x.score, 1)}</td>
          <td class="notes">${(x.notes || []).slice(0, 2).join(" · ")}</td></tr>`
        )
        .join("") || `<tr><td colspan="6">无</td></tr>`;
    $("leaderSummary").innerHTML = `
      <span class="badge">领涨 ${data.leaders?.length || 0}</span>
      <span class="badge">观察 ${data.watch?.length || 0}</span>
      <span class="badge">涨停 ${data.stats?.limit_up ?? "—"}</span>`;
    bindRows($("leaderBody"));
    bindRows($("anchorBody"));
    bindRows($("watchBody"));
  }
  async function refresh() {
    state.date = $("dateSelect").value || state.date;
    state.source = $("sourceSelect").value || state.source;
    $("statusPill").textContent = "选股计算中…";
    try {
      const data = await api(`/api/screen?date=${encodeURIComponent(state.date)}&source=${encodeURIComponent(state.source)}`);
      renderHot(data.hot_boards || []);
      renderTables(data);
      $("statusPill").textContent = `数据源 ${data.source || state.source} · ${data.date}`;
      const t = data.theory || {};
      $("theoryPill").textContent = t.xian ? `${t.xian} ｜ ${t.bi} ｜ ${t.du}` : "先 / 比 / 独";
      $("updatedPill").textContent = `更新 ${data.updated_at || ""}`;
      if (data.warnings?.length) $("statusPill").textContent += ` · ${data.warnings[0]}`;
    } catch (err) {
      $("statusPill").textContent = `加载失败：${err.message}`;
    }
  }
  function renderDay(bars) {
    const cats = bars.map((b) => b.time);
    state.charts.day.setOption({
      backgroundColor: "transparent",
      animation: false,
      grid: [{ left: 48, right: 16, top: 18, height: "58%" }, { left: 48, right: 16, top: "78%", height: "14%" }],
      xAxis: [
        { type: "category", data: cats, ...axis(), axisLabel: { show: false } },
        { type: "category", data: cats, gridIndex: 1, ...axis(), axisLabel: { color: "#5c6775", fontSize: 10 } },
      ],
      yAxis: [
        { scale: true, ...axis() },
        { scale: true, gridIndex: 1, splitNumber: 2, ...axis(), axisLabel: { show: false } },
      ],
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1], start: 55, end: 100 }],
      series: [
        {
          type: "candlestick",
          data: bars.map((b) => [b.open, b.close, b.low, b.high]),
          itemStyle: { color: "#c62828", color0: "#1b7f4b", borderColor: "#c62828", borderColor0: "#1b7f4b" },
        },
        { type: "bar", data: bars.map((b) => b.volume), xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: "#9bb7ad" } },
      ],
    });
  }
  function renderMinute(minute) {
    const points = minute.points || [];
    const pre = Number(minute.pre_close || points[0]?.price || 0);
    const times = points.map((p) => p.time);
    state.charts.minute.setOption({
      backgroundColor: "transparent",
      animation: false,
      grid: [{ left: 48, right: 16, top: 20, height: "58%" }, { left: 48, right: 16, top: "78%", height: "14%" }],
      xAxis: [
        { type: "category", data: times, boundaryGap: false, ...axis(), axisLabel: { show: false } },
        { type: "category", data: times, gridIndex: 1, ...axis(), axisLabel: { color: "#5c6775", fontSize: 10 } },
      ],
      yAxis: [
        { scale: true, ...axis(), axisLabel: { color: "#5c6775", formatter: (v) => Number(v).toFixed(2) } },
        { scale: true, gridIndex: 1, ...axis(), axisLabel: { show: false } },
      ],
      series: [
        {
          type: "line",
          data: points.map((p) => p.price),
          showSymbol: false,
          lineStyle: { width: 1.5, color: "#1c2430" },
          areaStyle: { color: "rgba(15,107,92,0.08)" },
          markLine: pre
            ? { symbol: "none", label: { show: false }, data: [{ yAxis: pre }], lineStyle: { type: "dashed", color: "#2a6f97" } }
            : undefined,
        },
        { type: "line", data: points.map((p) => p.avg), showSymbol: false, lineStyle: { width: 1, color: "#2a6f97" } },
        { type: "bar", data: points.map((p) => p.volume), xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: "#9bb7ad" } },
      ],
    });
  }
  function renderIntra(bars) {
    state.charts.intra.setOption({
      backgroundColor: "transparent",
      animation: false,
      grid: { left: 48, right: 16, top: 18, bottom: 28 },
      xAxis: { type: "category", data: bars.map((b) => String(b.time || "").slice(5)), ...axis() },
      yAxis: { scale: true, ...axis() },
      series: [
        {
          type: "line",
          data: bars.map((b) => b.close),
          showSymbol: false,
          lineStyle: { width: 1.4, color: "#0f6b5c" },
          areaStyle: { color: "rgba(15,107,92,0.1)" },
        },
      ],
    });
  }
  function renderDepth(depth) {
    const asks = [...(depth.asks || [])].reverse();
    const bids = depth.bids || [];
    $("depthBox").innerHTML = `
      <div class="depth-meta">最新 ${fmtNum(depth.price)} · 昨收 ${fmtNum(depth.pre_close)} · ${depth.source || ""}</div>
      <div class="depth-side">${
        asks.map((x, i) => `<div class="depth-row ask"><span>卖${asks.length - i}</span><span>${fmtNum(x.price)} / ${fmtNum(x.volume, 0)}</span></div>`).join("") ||
        "<div class='depth-row'>无卖档</div>"
      }</div>
      <div class="depth-side">${
        bids.map((x, i) => `<div class="depth-row bid"><span>买${i + 1}</span><span>${fmtNum(x.price)} / ${fmtNum(x.volume, 0)}</span></div>`).join("") ||
        "<div class='depth-row'>无买档</div>"
      }</div>`;
  }
  async function openPanel(code, name) {
    $("tspMask").classList.remove("hidden");
    $("tspPanel").classList.remove("hidden");
    $("tspTitle").textContent = `${name || ""} ${code}`;
    $("tspSub").textContent = "加载 Tick Stock Panel…";
    const source = $("tspChartSource").value || "tdx";
    try {
      const data = await api(`/api/panel/${code}?source=${encodeURIComponent(source)}`);
      state.panel = { ...data, code };
      $("tspSub").textContent = `Tick Stock Panel · ${data.source || source}${data.errors?.length ? " · 部分降级" : ""}`;
      renderDay(data.day || []);
      renderMinute(data.minute || { points: [] });
      renderIntra((state.intraPeriod === "5min" ? data.m5 : data.m1) || []);
      renderDepth(data.depth || {});
      setTimeout(() => Object.values(state.charts).forEach((c) => c && c.resize()), 40);
    } catch (err) {
      $("tspSub").textContent = `加载失败：${err.message}`;
    }
  }
  function closePanel() {
    $("tspMask").classList.add("hidden");
    $("tspPanel").classList.add("hidden");
  }
  async function shot(el, filename) {
    if (!window.html2canvas) return alert("截图组件未加载");
    const canvas = await html2canvas(el, { backgroundColor: "#eef3f1", scale: window.devicePixelRatio > 1 ? 2 : 1, useCORS: true });
    const a = document.createElement("a");
    a.href = canvas.toDataURL("image/png");
    a.download = filename;
    a.click();
  }
  function bind() {
    $("btnRefresh").onclick = refresh;
    $("dateSelect").onchange = refresh;
    $("sourceSelect").onchange = refresh;
    $("btnShot").onclick = () => shot($("captureRoot"), `xianbidu_${state.date || "today"}.png`);
    $("tspClose").onclick = closePanel;
    $("tspMask").onclick = closePanel;
    $("tspShot").onclick = () => shot($("tspCapture"), `tsp_${Date.now()}.png`);
    $("tspChartSource").onchange = () => {
      if (state.panel?.code) openPanel(state.panel.code, $("tspTitle").textContent);
    };
    document.querySelectorAll(".mini-tab").forEach((btn) => {
      btn.onclick = () => {
        document.querySelectorAll(".mini-tab").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.intraPeriod = btn.dataset.period;
        if (state.panel) renderIntra((state.intraPeriod === "5min" ? state.panel.m5 : state.panel.m1) || []);
      };
    });
  }
  async function boot() {
    initCharts();
    bind();
    await loadSources();
    await loadDates();
    await refresh();
  }
  boot();
})();