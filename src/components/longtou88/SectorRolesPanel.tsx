import { formatAmount, formatPercent } from "@/lib/format";
import type { LT88SectorSnapshot } from "@/lib/longtou88/types";
import { RoleStockCard } from "./RoleStockCard";

const RANK_BADGE = ["①", "②", "③"];

const ROLE_STYLE: Record<string, string> = {
  连板龙头: "border-up/35 bg-up/5",
  趋势龙头: "border-gold/35 bg-gold/5",
  中军: "border-[#6eb5ff]/35 bg-[#6eb5ff]/5",
  跟风: "border-line bg-elev/70",
  补涨: "border-line bg-elev/70",
  卡位: "border-warn/35 bg-warn/5",
};

export function SectorRolesPanel({ sector }: { sector: LT88SectorSnapshot }) {
  return (
    <section className="rounded-2xl border border-line bg-elev/85 p-4">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs text-gold">{RANK_BADGE[sector.rank - 1] ?? sector.rank} 热点板块</p>
          <h2 className="text-xl font-semibold text-[#6eb5ff]">{sector.name}</h2>
          <p className="mt-1 text-xs text-muted">
            涨停 {sector.limitUpCount} · 炸板 {sector.brokenCount} · 成分 {sector.memberCount}
          </p>
        </div>
        <div className="text-right text-sm">
          <div className="tabular text-up">{formatPercent(sector.changePercent)}</div>
          <div className="tabular text-xs text-muted">{formatAmount(sector.amount)}</div>
        </div>
      </header>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {sector.roles.map((group) => (
          <div
            key={group.role}
            className={`rounded-xl border p-3 ${ROLE_STYLE[group.role] ?? "border-line bg-elev/70"}`}
          >
            <div className="mb-2">
              <h3 className="text-sm font-semibold text-ink">{group.role}</h3>
              <p className="mt-0.5 text-[11px] leading-5 text-muted">{group.hint}</p>
            </div>
            {group.stocks.length ? (
              <div className="space-y-2">
                {group.stocks.map((stock) => (
                  <RoleStockCard key={stock.code} stock={stock} />
                ))}
              </div>
            ) : (
              <p className="rounded-lg border border-dashed border-line px-3 py-6 text-center text-xs text-muted">
                暂无符合该角色的标的
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
