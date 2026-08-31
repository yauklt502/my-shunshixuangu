import { formatAmount, formatPercent } from "@/lib/format";
import type { TrendSectorSnapshot } from "@/lib/qushi-longtou/types";
import { TrendLeaderCard } from "./TrendLeaderCard";

const RANK_BADGE = ["①", "②", "③"];

export function TrendSectorPanel({ sector }: { sector: TrendSectorSnapshot }) {
  return (
    <section className="rounded-2xl border border-line bg-elev/85 p-4">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs text-gold">{RANK_BADGE[sector.rank - 1] ?? sector.rank} 热点板块</p>
          <h2 className="text-xl font-semibold text-[#6eb5ff]">{sector.name}</h2>
          <p className="mt-1 text-xs text-muted">
            成分 {sector.memberCount} · 涨 {sector.upCount ?? "--"} / 跌 {sector.downCount ?? "--"}
            {sector.sectorSync ? (
              <span className="ml-2 text-down">板块有配合</span>
            ) : (
              <span className="ml-2 text-warn">板块共振偏弱</span>
            )}
          </p>
        </div>
        <div className="text-right text-sm">
          <div className="tabular text-up">{formatPercent(sector.changePercent)}</div>
          <div className="tabular text-xs text-muted">{formatAmount(sector.amount)}</div>
        </div>
      </header>

      {sector.leaders.length ? (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {sector.leaders.map((leader) => (
            <TrendLeaderCard key={leader.code} leader={leader} />
          ))}
        </div>
      ) : (
        <p className="rounded-xl border border-dashed border-line px-4 py-8 text-center text-sm text-muted">
          暂无符合五维条件的趋势龙头（需至少满足 3/5，且非涨停）
        </p>
      )}
    </section>
  );
}
