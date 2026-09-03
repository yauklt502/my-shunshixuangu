(function () {
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const html = document.documentElement;
  const fileMode = location.protocol === "file:";

  const todayCN = () => {
    const now = new Date();
    const cn = new Date(now.getTime() + 8 * 3600 * 1000);
    return cn.toISOString().slice(0, 10);
  };

  const defaultDate =
    params.get("date") ||
    html.dataset.defaultDate ||
    $("date-input")?.value ||
    "2026-09-03";
  const defaultTheme = params.get("theme") || html.dataset.theme || html.getAttribute("data-theme") || "dark";

  let current = null;
  let autoTimer = null;
  let loading = false;

  function scoreCell(v) {
    if (v >= 0.99) return ["1", "ok"];
    if (v >= 0.4) return ["½", "half"];
    return ["0", "no"];
  }

  function setTheme(theme) {
    html.setAttribute("data-theme", theme);
    html.dataset.theme = theme;
    const btn = $("btn-theme");
    if (btn) btn.textContent = theme === "light" ? "深色" : "浅色";
    try {
      localStorage.setItem("zhenlong-theme", theme);
    } catch (_) {}
  }

  function setStatus(text, cls) {
    const el = $("status");
    if (!el) return;
    el.className = "status" + (cls ? " " + cls : "");
    el.textContent = text;
  }

  function syncUrl(date) {
    if (fileMode) return;
    const next = new URL(location.href);
    next.searchParams.set("date", date);
    next.searchParams.set("theme", html.getAttribute("data-theme") || "dark");
    history.replaceState(null, "", next);
  }

  function render(data) {
    current = data;
    const date = data.date || defaultDate;
    const title = $("card-title-date");
    if (title) title.innerHTML = data.title_suffix || date;
    document.title = "真龙识别 · " + (data.title_suffix || date) + "盯盘卡";
    const sub = $("card-sub");
    if (sub) sub.innerHTML = data.subtitle || "";

    const tldr = $("tldr");
    if (tldr && data.tldr) {
      const lines = (data.tldr.lines || [])
        .map((line) => `<div class="v">${line}</div>`)
        .join("");
      tldr.innerHTML =
        `<div class="k">一句话结论</div>` +
        `<div class="v ${data.tldr.verdict_class || ""}">${data.tldr.verdict || ""}</div>` +
        lines;
    }

    const warn = $("warn");
    if (warn) warn.innerHTML = data.warn || "";

    const table = $("score-table");
    if (table) {
      const rows = (data.table || [])
        .map((row) => {
          const [d, dc] = scoreCell(row.drive);
          const [l, lc] = scoreCell(row.lead);
          const [s, sc] = scoreCell(row.survive);
          const [q, qc] = scoreCell(row.liq);
          const nameCls = row.fallen ? ' style="color:var(--red2)"' : "";
          return `<tr>
            <td class="name"${nameCls}>${row.name}<br><span class="note">${row.code} ${row.theme || ""}</span></td>
            <td class="${row.fallen ? "red" : ""}">${row.boards}</td>
            <td class="${dc}">${d}</td>
            <td class="${lc}">${l}</td>
            <td class="${sc}">${s}</td>
            <td class="${qc}">${q}</td>
            <td class="${row.score_class || ""}">${row.score_class ? row.score : "<b>" + row.score + "</b>"}</td>
            <td class="${row.verdict_class || "note"}">${row.verdict}</td>
          </tr>`;
        })
        .join("");
      table.innerHTML =
        `<tr><th>标的</th><th>连板</th><th>带动性</th><th>领涨性</th><th>渡劫能力</th><th>顶级流动性</th><th>真龙指数</th><th>判定</th></tr>` +
        (rows || `<tr><td colspan="8" class="note">暂无数据</td></tr>`);
    }

    const scoreNote = $("score-note");
    if (scoreNote && data.score_note) scoreNote.textContent = data.score_note;

    const boxes = $("boxes");
    if (boxes) {
      boxes.innerHTML = (data.boxes || [])
        .map((box) => {
          const tags = (box.tags || [])
            .map((t) => `<span class="tag ${t.c || ""}">${t.t}</span>`)
            .join("");
          const notes = (box.notes || [])
            .map((n, i) => `<div class="note"${i === 0 ? ' style="margin-top:8px"' : ""}>${n}</div>`)
            .join("");
          const border = box.danger ? ' style="border-color:var(--danger-line)"' : "";
          const ttlStyle = box.danger ? ' style="color:var(--red2)"' : "";
          return `<div class="box"${border}><div class="ttl"${ttlStyle}>${box.title}</div>${tags}${notes}</div>`;
        })
        .join("");
    }

    const ladderTitle = $("ladder-title");
    if (ladderTitle) ladderTitle.textContent = data.ladder_title || "三、连板梯队";
    const ladder = $("ladder-table");
    if (ladder) {
      const rows = (data.ladder || [])
        .map(
          (r) =>
            `<tr><td class="name">${r.level}</td><td>${r.names}</td><td class="note">${r.attr}</td></tr>`
        )
        .join("");
      ladder.innerHTML =
        `<tr><th>层级</th><th>标的</th><th>属性</th></tr>` +
        (rows || `<tr><td colspan="3" class="note">暂无连板</td></tr>`);
    }
    const ladderNote = $("ladder-note");
    if (ladderNote) ladderNote.innerHTML = data.ladder_note || "";

    const watchTitle = $("watch-title");
    if (watchTitle) watchTitle.textContent = data.watch_title || "四、盯盘清单";
    const watch = $("watch-box");
    if (watch && data.watch) {
      const notes = (data.watch.notes || [])
        .map((n, i, arr) => {
          const last = i === arr.length - 1 && n.includes("口诀");
          return `<div class="note"${last ? ' style="color:var(--amber)"' : ""}>${n}</div>`;
        })
        .join("");
      watch.innerHTML = `<div class="ttl">${data.watch.title || ""}</div>${notes}`;
    }

    const foot = $("foot");
    if (foot) foot.innerHTML = data.foot || "";

    const src = data.source === "snapshot" ? "精选快照" : data.source === "cache" ? "本地缓存" : "实时接入";
    const sess = data.session_label || "";
    setStatus(`${date} · ${sess} · ${src} · 更新 ${data.updated_at || ""}`.trim(), data.in_session ? "live" : "");
  }

  async function load(date, refresh) {
    if (loading) return;
    loading = true;
    setStatus(refresh ? "正在拉取实时行情…" : "正在加载…", "busy");
    try {
      if (fileMode) {
        throw new Error("file");
      }
      const q = new URLSearchParams({ date, refresh: refresh ? "1" : "0" });
      const res = await fetch("/api/review?" + q.toString(), { cache: "no-store" });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "接口失败");
      render(data);
      syncUrl(date);
    } catch (err) {
      if ($("date-input")) $("date-input").value = date;
      if (window.EMBEDDED_SNAPSHOT && (!refresh || fileMode)) {
        const snap = Object.assign({ date, source: "snapshot", session_label: "收盘" }, window.EMBEDDED_SNAPSHOT);
        render(snap);
        if (!fileMode) setStatus("接口暂不可用，已显示本地快照", "busy");
        else setStatus("本地快照 · 启动 python3 server.py 后可盘中刷新 / 翻历史", "");
      } else {
        setStatus("加载失败：" + (err.message || err), "busy");
      }
    } finally {
      loading = false;
    }
  }

  function selectedDate() {
    return $("date-input")?.value || defaultDate;
  }

  function scheduleAuto() {
    if (autoTimer) {
      clearInterval(autoTimer);
      autoTimer = null;
    }
    if (!$("auto-refresh")?.checked) return;
    autoTimer = setInterval(() => {
      const date = selectedDate();
      const isToday = date === todayCN();
      if (!isToday) return;
      load(date, true);
    }, 30000);
  }

  async function shot() {
    const btn = $("btn-shot");
    if (btn) btn.disabled = true;
    setStatus("正在截屏…", "busy");
    const toolbar = $("toolbar");
    const card = $("card") || document.querySelector(".wrap");
    try {
      if (!window.html2canvas) throw new Error("截屏组件未加载");
      if (toolbar) toolbar.classList.add("shot-hide");
      const canvas = await window.html2canvas(card, {
        backgroundColor: getComputedStyle(document.body).backgroundColor,
        scale: 2,
        useCORS: true,
        logging: false,
      });
      const date = (current && current.date) || selectedDate();
      const a = document.createElement("a");
      a.download = `真龙识别_${date.replace(/-/g, "")}.png`;
      a.href = canvas.toDataURL("image/png");
      a.click();
      setStatus("截屏已保存 " + a.download, "live");
    } catch (err) {
      setStatus("截屏失败：" + (err.message || err), "busy");
    } finally {
      if (toolbar) toolbar.classList.remove("shot-hide");
      if (btn) btn.disabled = false;
    }
  }

  function init() {
    const storedTheme = (() => {
      try {
        return localStorage.getItem("zhenlong-theme");
      } catch (_) {
        return null;
      }
    })();
    setTheme(params.get("theme") || storedTheme || defaultTheme);

    const dateInput = $("date-input");
    const date = defaultDate;
    if (dateInput) dateInput.value = date;

    $("btn-today")?.addEventListener("click", () => {
      const t = todayCN();
      if (dateInput) dateInput.value = t;
      load(t, true);
    });
    $("btn-refresh")?.addEventListener("click", () => load(selectedDate(), true));
    $("btn-shot")?.addEventListener("click", shot);
    $("btn-theme")?.addEventListener("click", () => {
      const next = (html.getAttribute("data-theme") || "dark") === "dark" ? "light" : "dark";
      setTheme(next);
      syncUrl(selectedDate());
    });
    dateInput?.addEventListener("change", () => load(selectedDate(), false));
    $("auto-refresh")?.addEventListener("change", scheduleAuto);

    if (window.EMBEDDED_SNAPSHOT && date === (window.EMBEDDED_SNAPSHOT.date || "2026-09-03")) {
      render(Object.assign({ source: "snapshot", session_label: "收盘", date }, window.EMBEDDED_SNAPSHOT));
    }
    load(date, false);
    scheduleAuto();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
