(function () {
  const UP = "#dc2626";
  const DOWN = "#15803d";
  const AVG = "#a16207";
  const AXIS = "#6b7280";
  const GRID = "#e5e7eb";

  function nice(v) {
    if (v == null || Number.isNaN(v)) return "-";
    return Number(v).toFixed(2);
  }

  function drawGrid(ctx, x, y, w, h, rows) {
    ctx.strokeStyle = GRID;
    ctx.lineWidth = 1;
    for (let i = 0; i <= rows; i++) {
      const yy = y + (h * i) / rows;
      ctx.beginPath();
      ctx.moveTo(x, yy);
      ctx.lineTo(x + w, yy);
      ctx.stroke();
    }
  }

  function yScale(min, max, y, h) {
    const span = max - min || 1;
    return (v) => y + h - ((v - min) / span) * h;
  }

  window.drawTimeshare = function (canvas, minute) {
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    const pts = (minute && minute.points) || [];
    if (!pts.length) {
      ctx.fillStyle = AXIS;
      ctx.fillText("没有分时", 16, 24);
      return;
    }
    const padL = 52, padR = 12, padT = 12, volH = 56, gap = 8;
    const plotH = H - padT - volH - gap - 18;
    const plotW = W - padL - padR;
    const prices = pts.map((p) => p.price).filter((v) => v > 0);
    const avgs = pts.map((p) => p.avg).filter((v) => v && v > 0);
    let prev = minute.prev_close || prices[0];
    let lo = Math.min(prev, ...prices, ...(avgs.length ? avgs : prices));
    let hi = Math.max(prev, ...prices, ...(avgs.length ? avgs : prices));
    const padP = (hi - lo) * 0.08 || 0.05;
    lo -= padP; hi += padP;
    const y = yScale(lo, hi, padT, plotH);
    const n = 241;
    const x = (i) => padL + (plotW * i) / (n - 1);
    drawGrid(ctx, padL, padT, plotW, plotH, 4);
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "#9ca3af";
    ctx.beginPath();
    ctx.moveTo(padL, y(prev));
    ctx.lineTo(padL + plotW, y(prev));
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.strokeStyle = pts[pts.length - 1].price >= prev ? UP : DOWN;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    pts.forEach((p, i) => {
      const xx = x(i);
      const yy = y(p.price);
      if (i === 0) ctx.moveTo(xx, yy);
      else ctx.lineTo(xx, yy);
    });
    ctx.stroke();
    if (avgs.length) {
      ctx.strokeStyle = AVG;
      ctx.lineWidth = 1;
      ctx.beginPath();
      pts.forEach((p, i) => {
        if (!p.avg) return;
        const xx = x(i);
        const yy = y(p.avg);
        if (i === 0) ctx.moveTo(xx, yy);
        else ctx.lineTo(xx, yy);
      });
      ctx.stroke();
    }
    ctx.fillStyle = AXIS;
    ctx.font = "11px sans-serif";
    ctx.fillText(nice(hi), 6, padT + 10);
    ctx.fillText(nice(prev), 6, y(prev) + 4);
    ctx.fillText(nice(lo), 6, padT + plotH);
    const maxV = Math.max(...pts.map((p) => p.volume || 0), 1);
    const vy = H - 16;
    pts.forEach((p, i) => {
      const xx = x(i);
      const vh = ((p.volume || 0) / maxV) * volH;
      ctx.fillStyle = p.price >= prev ? "rgba(220,38,38,.45)" : "rgba(21,128,61,.45)";
      ctx.fillRect(xx, vy - vh, Math.max(1, plotW / n - 0.4), vh);
    });
    ctx.fillStyle = AXIS;
    ctx.fillText(pts[0].time, padL, H - 4);
    ctx.fillText(pts[pts.length - 1].time, W - 40, H - 4);
  };

  window.drawKline = function (canvas, bars) {
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    if (!bars || !bars.length) {
      ctx.fillStyle = AXIS;
      ctx.fillText("没有K线", 16, 24);
      return;
    }
    const padL = 52, padR = 12, padT = 12, volH = 56, gap = 8;
    const plotH = H - padT - volH - gap - 18;
    const plotW = W - padL - padR;
    const hi = Math.max(...bars.map((b) => b.high));
    const lo = Math.min(...bars.map((b) => b.low));
    const padP = (hi - lo) * 0.08 || 0.05;
    const y = yScale(lo - padP, hi + padP, padT, plotH);
    const n = bars.length;
    const cw = Math.max(2, plotW / n - 1.2);
    drawGrid(ctx, padL, padT, plotW, plotH, 4);
    const maxV = Math.max(...bars.map((b) => b.volume || 0), 1);
    bars.forEach((b, i) => {
      const xx = padL + (plotW * (i + 0.5)) / n;
      const up = b.close >= b.open;
      ctx.strokeStyle = up ? UP : DOWN;
      ctx.fillStyle = up ? UP : DOWN;
      ctx.beginPath();
      ctx.moveTo(xx, y(b.high));
      ctx.lineTo(xx, y(b.low));
      ctx.stroke();
      const top = y(Math.max(b.open, b.close));
      const bot = y(Math.min(b.open, b.close));
      ctx.fillRect(xx - cw / 2, top, cw, Math.max(1, bot - top));
      const vh = ((b.volume || 0) / maxV) * volH;
      ctx.globalAlpha = 0.45;
      ctx.fillRect(xx - cw / 2, H - 16 - vh, cw, vh);
      ctx.globalAlpha = 1;
    });
    ctx.fillStyle = AXIS;
    ctx.font = "11px sans-serif";
    ctx.fillText(nice(hi), 6, padT + 10);
    ctx.fillText(nice(lo), 6, padT + plotH);
    ctx.fillText((bars[0].time || "").slice(0, 10), padL, H - 4);
    ctx.fillText((bars[bars.length - 1].time || "").slice(0, 10), W - 80, H - 4);
  };
})();
