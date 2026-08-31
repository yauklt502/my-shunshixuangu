import { LeaderCard } from "@/components/LeaderCard";
import { Sparkline } from "@/components/Sparkline";
import { boardUrl, formatAmount, formatPercent, signedClass } from "@/lib/format";
import type { SectorSnapshot } from "@/lib/types";

const RANK_MARK = ["①", "②", "③"];

export function SectorColumn({ sector }: { sector: SectorSnapshot }) {
  const tone = signedClass(sector.changePercent);
  return (
    <section className="flex min-h-0 flex-col rounded-2xl border border-line bg-elev/85 p-3 shadow-[0_12px_40px_rgba(0,0,0,0.25)] backdrop-blur">
      <header className="mb-3">
        <div className="flex items-start justify-between gap-2">
          <a href={boardUrl(sector.code)} target="_blank" rel="noreferrer" className="min-w-0">
            <p className="text-xs text-muted">
              {RANK_MARK[sector.rank - 1]} {sector.kind === "concept" ? "概念" : "行业"} · {sector.code}
            </p>
            <h2 className="truncate text-xl font-semibold tracking-tight text-ink">{sector.name}</h2>
          </a>
          <div className="text-right">
            <div className={`tabular text-2xl font-semibold leading-none ${tone === "down" ? "text-down" : "text-up"}`}>
              {formatPercent(sector.changePercent)}
            </div>
            <p className="mt-1 text-[11px] text-muted">板块涨幅</p>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted">
          <span>成分 {sector.memberCount}</span>
          <span className="text-up">涨停 {sector.limitUpCount}</span>
          <span className="text-warn">炸板 {sector.brokenCount}</span>
          <span>上涨 {sector.upCount ?? "--"}</span>
          <span>成交 {formatAmount(sector.amount, 1)}</span>
          <span>主力 {formatAmount(sector.mainNetInflow, 1)}</span>
        </div>
        <Sparkline className="mt-2 h-12" points={sector.trend} tone={tone === "flat" ? "gold" : tone} />
      </header>
      <div className="flex flex-1 flex-col gap-2">
        {sector.leaders.map((leader) => (
          <LeaderCard key={leader.code} leader={leader} />
        ))}
        {sector.leaders.length === 0 ? (
          <p className="rounded-xl border border-dashed border-line p-6 text-center text-sm text-muted">
            该板块暂无有效成分股
          </p>
        ) : null}
      </div>
    </section>
  );
}
