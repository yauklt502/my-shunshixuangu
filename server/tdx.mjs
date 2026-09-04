import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const bridge = path.join(__dirname, "tdx_bridge.py");

const TDX_HTTP = process.env.TDX_HTTP_URL || "http://127.0.0.1:8790";
const TDX_HOST = process.env.TDX_HOST || "115.238.90.165:7709";
const TDX_TIMEOUT = process.env.TDX_TIMEOUT || "8";

function pythonBin() {
  return process.env.TDX_PYTHON || process.env.PYTHON || "python3";
}

function runBridge(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(pythonBin(), [bridge, ...args], {
      env: { ...process.env, TDX_HOST, TDX_TIMEOUT },
    });
    let out = "";
    let err = "";
    child.stdout.on("data", (chunk) => {
      out += chunk;
    });
    child.stderr.on("data", (chunk) => {
      err += chunk;
    });
    child.on("error", reject);
    child.on("close", (code) => {
      try {
        const data = JSON.parse(out || "{}");
        if (!data.ok) {
          reject(new Error(data.errmsg || err || `tdx bridge exit ${code}`));
          return;
        }
        resolve(data.result);
      } catch (error) {
        reject(new Error(err || out || error.message || "tdx bridge parse failed"));
      }
    });
  });
}

async function rpcHttp(method, params) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(`${TDX_HTTP}/rpc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ method, params }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error?.message || "tdx rpc failed");
    return data.result;
  } finally {
    clearTimeout(timer);
  }
}

function normalizeBars(series) {
  return {
    code: series.code,
    exchange: series.exchange,
    period: series.period || series.period_name,
    bars: (series.bars || []).map((bar) => ({
      time: bar.time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume ?? bar.volume_lots,
      amount: bar.amount,
      last_close: bar.last_close ?? (bar.last_close_price_milli ? bar.last_close_price_milli / 1000 : null),
    })),
  };
}

function normalizeMinutes(series) {
  return {
    code: series.code,
    exchange: series.exchange,
    trading_date: series.trading_date,
    prev_close: series.prev_close,
    points: (series.points || []).map((point) => ({
      time: point.time || point.time_label,
      price: point.price,
      avg: point.avg ?? point.avg_price,
      volume: point.volume,
    })),
  };
}

export async function fetchKline(code, period = "day", count = 120) {
  try {
    const series = await rpcHttp("bars.get", { code, period, count, adjust: "qfq" });
    return normalizeBars(series);
  } catch {
    return runBridge(["kline", "--code", code, "--period", period, "--count", String(count)]);
  }
}

export async function fetchMinute(code, date = "") {
  try {
    const series = date
      ? await rpcHttp("minutes.history", { code, trading_date: date })
      : await rpcHttp("minutes.today", { code });
    return normalizeMinutes(series);
  } catch {
    const args = ["minute", "--code", code];
    if (date) args.push("--date", date);
    return runBridge(args);
  }
}

export function tdxAvailable() {
  return fs.existsSync(bridge);
}
