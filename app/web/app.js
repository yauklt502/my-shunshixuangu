(() => {
  const $ = (id) => document.getElementById(id);
  const state = {
    mode: "optimized",
    result: null,
    watching: false,
    timer: null,
    formulas: [],
  };

  function toast(msg) {
    const el = $("toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 2800);
  }

  async function api(path) {
    const res = await fetch(path, { cache: "no-store" });
    const data = await res.json();
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
  }

  function setBusy(busy, label) {
    ["btnScan", "btnPreopen", "btnWatch", "btnExport"].forEach((id) => {
      const b = $(id);
      if (id === "btnWatch") return;
      b.disabled = busy;
    });
    if (busy) toast(label || "运行中…");
  }

  function renderStrategies(list) {
    const box = $("strategies");
    box.innerHTML = "";
    list.forEach((s) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = s.id === state.mode ? "on" : "";
      btn.innerHTML = `<span class="name">${s.name}</span><span class="desc">${s.desc}</span>`;
      btn.onclick = () => {
        state.mode = s.id;
        [...box.children].forEach((c) => c.classList.remove("on"));
        btn.classList.add("on");
        $("resultTitle").textContent = s.name;
        $("resultSub").textContent = s.desc;
      };
      box.appendChild(btn);
    });
  }

  function trajTag(label) {
    if (!label) return "";
    let cls = "tag";
    if (label.includes("回落") || label.includes("弱势")) cls += " bad";
    else if (label.includes("观察") || label.includes("不足")) cls += " warn";
    return `<span class="${cls}">${label}</span>`;
  }

  function renderResult(data) {
    state.result = data;
    $("resultTitle").textContent = data.title || "扫描结果";
    $("resultSub").textContent = `${data.generated_at || ""} · 昨涨停 ${data.zt_date || "-"} · ${data.tip || ""}`;
    $("statTop").textContent = String((data.top || []).length);
    $("statMain").textContent = String(data.main_n || 0);
    $("statFetched").textContent = String(data.fetched || data.quoted || 0);
    $("tipBox").textContent = data.tip || "";
    $("meta").innerHTML = `策略 <strong>${data.mode}</strong> · 耗时 <strong>${data.elapsed_sec ?? "-"}</strong>s · 错误 ${data.errors_n ?? 0}`;

    const cards = $("cards");
    const top = data.top || [];
    if (!top.length) {
      cards.innerHTML = `<div class="empty">过滤后无标的。可换策略，或等 9:25 后再扫。</div>`;
    } else {
      cards.innerHTML = top
        .map((r, i) => {
          const why = (r.reasons || []).slice(0, 4).join("；");
          const tp = r.tp_hint ? ` · 止盈+${(r.tp_hint * 100).toFixed(1)}%` : "";
          return `<article class="pick">
            <div class="rank">TOP ${i + 1}${tp}</div>
            <h4>${r.name || ""}<span>${r.code || ""}</span></h4>
            <div class="pct">${Number(r.open_pct || 0).toFixed(2)}%</div>
            <dl>
              <div><dt>高度</dt><dd>${r.lbc ?? "-"}板</dd></div>
              <div><dt>分数</dt><dd>${r.score ?? "-"}</dd></div>
              <div><dt>竞价量</dt><dd>${r.auction_wan ?? ((r.auction_shares || 0) / 1e4).toFixed(0)}万</dd></div>
              <div><dt>量比</dt><dd>${Number(r.vol_ratio || 0).toFixed(1)}</dd></div>
              <div><dt>换手</dt><dd>${Number(r.turnover || 0).toFixed(3)}%</dd></div>
              <div><dt>金额比</dt><dd>${Number(r.amt_ratio || 0).toFixed(2)}</dd></div>
            </dl>
            <div class="why">${why || r.traj_label || ""}</div>
          </article>`;
        })
        .join("");
    }

    const rows = (data.pool && data.pool.length ? data.pool : top) || [];
    const tb = $("tbody");
    if (!rows.length) {
      tb.innerHTML = `<tr><td colspan="12" class="empty">暂无数据</td></tr>`;
      return;
    }
    tb.innerHTML = rows
      .map((r, i) => {
        const wan = r.auction_wan ?? ((r.auction_shares || 0) / 1e4);
        return `<tr>
          <td>${i + 1}</td>
          <td class="mono">${r.code || ""}</td>
          <td>${r.name || ""}</td>
          <td class="up mono">${Number(r.open_pct || 0).toFixed(2)}%</td>
          <td class="mono">${r.lbc ?? ""}</td>
          <td class="mono">${Number(wan).toFixed(1)}</td>
          <td class="mono">${Number(r.vol_ratio || 0).toFixed(1)}</td>
          <td class="mono">${Number(r.turnover || 0).toFixed(3)}</td>
          <td class="mono">${Number(r.amt_ratio || 0).toFixed(2)}</td>
          <td class="mono">${r.score ?? "-"}</td>
          <td>${trajTag(r.traj_label)}</td>
          <td>${r.hy || ""}</td>
        </tr>`;
      })
      .join("");
  }

  async function refreshPhase() {
    try {
      const d = await api("/api/phase");
      $("clock").textContent = d.clock;
      $("phaseTip").textContent = d.tip;
    } catch (_) {
      $("phaseTip").textContent = "服务未连接";
    }
  }

  async function runScan() {
    setBusy(true, "正在拉取昨涨停与竞价…约需几十秒");
    try {
      const data = await api(`/api/scan?mode=${encodeURIComponent(state.mode)}&top=5`);
      renderResult(data);
      toast(`完成：${(data.top || []).length} 只`);
    } catch (e) {
      toast(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  async function runPreopen() {
    setBusy(true, "盘前快照…首次会缓存昨涨停池");
    try {
      const data = await api(`/api/preopen?mode=${encodeURIComponent(state.mode)}&top=5`);
      renderResult(data);
      toast(`盘前：${(data.top || []).length} 只 · ${data.phase?.tip || ""}`);
    } catch (e) {
      toast(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  function toggleWatch() {
    state.watching = !state.watching;
    const btn = $("btnWatch");
    if (state.watching) {
      btn.textContent = "停止自动刷新";
      btn.classList.add("btn-amber");
      btn.classList.remove("btn-ghost");
      runPreopen();
      state.timer = setInterval(runPreopen, 15000);
      toast("已开启 15 秒盘前刷新");
    } else {
      btn.textContent = "自动刷新（15s）";
      btn.classList.remove("btn-amber");
      btn.classList.add("btn-ghost");
      clearInterval(state.timer);
      toast("已停止自动刷新");
    }
  }

  function exportJson() {
    if (!state.result) {
      toast("还没有结果");
      return;
    }
    const blob = new Blob([JSON.stringify(state.result, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `顺势竞价-${state.result.mode}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function loadFormulas() {
    try {
      const d = await api("/api/formulas");
      state.formulas = d.formulas || [];
      $("formulaBox").innerHTML = state.formulas
        .map(
          (f) =>
            `<details style="margin-top:8px"><summary>${f.name}</summary><pre>${f.text
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")}</pre></details>`
        )
        .join("");
    } catch (_) {
      /* ignore */
    }
  }

  async function boot() {
    const strat = await api("/api/strategies");
    renderStrategies(strat.strategies || []);
    await refreshPhase();
    await loadFormulas();
    try {
      const last = await api("/api/last");
      if (last.result) renderResult(last.result);
    } catch (_) {
      /* ignore */
    }
    setInterval(refreshPhase, 1000);
  }

  $("btnScan").onclick = runScan;
  $("btnPreopen").onclick = runPreopen;
  $("btnWatch").onclick = toggleWatch;
  $("btnExport").onclick = exportJson;

  boot().catch((e) => toast(String(e.message || e)));
})();
