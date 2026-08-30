import type { MarketSession } from "./types";

function beijingWeekday(date: Date): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Shanghai",
    weekday: "short",
  }).format(date);
}

function beijingMinutes(date: Date): number {
  const clock = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Shanghai",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date);
  const [hour, minute] = clock.split(":").map(Number);
  return hour * 60 + minute;
}

export function getMarketSession(date = new Date()): MarketSession {
  const weekday = beijingWeekday(date);
  if (weekday === "Sat" || weekday === "Sun") return "weekend";

  const mins = beijingMinutes(date);
  if (mins < 9 * 60 + 15) return "pre";
  if (mins < 9 * 60 + 25) return "auction";
  if (mins < 11 * 60 + 30) return "morning";
  if (mins < 13 * 60) return "lunch";
  if (mins < 15 * 60 + 5) return "afternoon";
  return "closed";
}

export function isLiveSession(session: MarketSession): boolean {
  return session === "auction" || session === "morning" || session === "afternoon";
}

export function pollIntervalMs(session: MarketSession): number {
  if (isLiveSession(session)) return 5000;
  if (session === "lunch") return 15000;
  return 30000;
}

export function sessionLabel(session: MarketSession): string {
  switch (session) {
    case "pre":
      return "未开盘";
    case "auction":
      return "集合竞价";
    case "morning":
      return "上午交易";
    case "lunch":
      return "午间休市";
    case "afternoon":
      return "下午交易";
    case "weekend":
      return "周末休市";
    default:
      return "已收盘";
  }
}
