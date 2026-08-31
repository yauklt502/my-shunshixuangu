import type { MarketSnapshot, WatchEvent } from "./types";

function leaderKey(sectorCode: string, stockCode: string): string {
  return `${sectorCode}:${stockCode}`;
}

export function diffSnapshots(
  prev: MarketSnapshot | null,
  next: MarketSnapshot,
): WatchEvent[] {
  if (!prev) return [];
  const events: WatchEvent[] = [];
  const prevSectors = new Map(prev.sectors.map((sector) => [sector.rank, sector]));
  const prevByStock = new Map(
    prev.sectors.flatMap((sector) =>
      sector.leaders.map((leader) => [leaderKey(sector.code, leader.code), { sector, leader }] as const),
    ),
  );

  for (const sector of next.sectors) {
    const oldSector = prevSectors.get(sector.rank);
    if (oldSector && oldSector.code !== sector.code) {
      events.push({
        id: `${next.updatedAt}:板块轮换:${sector.rank}:${sector.code}`,
        at: next.updatedAt,
        kind: "板块轮换",
        sectorName: sector.name,
        stockName: sector.name,
        stockCode: sector.code,
        detail: `第${sector.rank}板块由 ${oldSector.name} 换成 ${sector.name}`,
      });
    }

    for (const leader of sector.leaders) {
      const old = prevByStock.get(leaderKey(sector.code, leader.code))?.leader;
      if (!old) continue;
      if (!old.isLimitUp && leader.isLimitUp) {
        events.push({
          id: `${next.updatedAt}:封板:${leader.code}`,
          at: next.updatedAt,
          kind: old.isBroken ? "回封" : "封板",
          sectorName: sector.name,
          stockName: leader.name,
          stockCode: leader.code,
          detail: `${leader.rank} ${leader.reason}`,
        });
      } else if (old.isLimitUp && !leader.isLimitUp) {
        events.push({
          id: `${next.updatedAt}:开板:${leader.code}`,
          at: next.updatedAt,
          kind: "开板",
          sectorName: sector.name,
          stockName: leader.name,
          stockCode: leader.code,
          detail: `${leader.rank} 打开涨停${leader.isBroken ? "（炸板）" : ""}`,
        });
      } else if (
        old.consecutiveBoards &&
        leader.consecutiveBoards &&
        leader.consecutiveBoards > old.consecutiveBoards
      ) {
        events.push({
          id: `${next.updatedAt}:晋级:${leader.code}:${leader.consecutiveBoards}`,
          at: next.updatedAt,
          kind: "晋级",
          sectorName: sector.name,
          stockName: leader.name,
          stockCode: leader.code,
          detail: `${leader.rank} 连板升至 ${leader.consecutiveBoards} 板`,
        });
      }
    }
  }

  return events;
}
