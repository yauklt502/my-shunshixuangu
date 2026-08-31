import {
  formatAmount,
  formatPercent,
  formatPrice,
  quoteUrl,
  signedClass,
} from "@/lib/format";
import type { MarketLeader, MarketLeaderRank } from "@/lib/types";

const RANK_STYLE: Record<MarketLeaderRank, string> = {
  总龙头: "bg-gold/20 text-gold border-gold/50 shadow-[0_0_24px_rgba(231,184,76,0.12)]",
  龙二: "bg-silver/10 text-silver border-silver/30",
  龙三: "bg-bronze/15 text-bronze border-bronze/35",
};

function LeaderTile({ leader }: { leader: MarketLeader }) {
  const tone = signedClass(leader.changePercent);
  const wrap = leader.isLimitUp ? "zt-glow" : leader.isBroken ? "broken-glow" : "";

  return (
    <a
      href={quoteUrl(leader.market, leader.code)}
      target="_blank"
      rel="noreferrer"
      className={`block rounded-xl border border-line bg-elev/90 p-3 transition hover:border-gold/40 ${wrap} ${leader.rank === "总龙头" ? "md:scale-[1.02]" : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${RANK_STYLE[leader.rank]}`}
            >
              {leader.rank}
            </span>
            {leader.isLimitUp ? (
              <span className="rounded bg-up/15 px-1.5 py-0.5 text-[11px] text-up">涨停</span>
            ) : null}
            {leader.consecutiveBoards && leader.consecutiveBoards > 1 ? (
              <span className="text-[11px] text-gold">{leader.consecutiveBoards}连板</span>
            ) : null}
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <h3 className="truncate text-base font-semibold text-ink">{leader.name}</h3>
            <span className="font-mono text-xs text-muted">{leader.code}</span>
          </div>
          {leader.sectorName ? (
            <p className="mt-1 truncate text-[11px] text-muted">{leader.sectorName}</p>
          ) : null}
        </div>
        <div className="shrink-0 text-right">
          <div
            className={`tabular text-lg font-semibold leading-none ${tone === "down" ? "text-down" : "text-up"}`}
          >
            {formatPercent(leader.changePercent)}
          </div>
          <div className="tabular mt-1 text-sm text-muted">{formatPrice(leader.price)}</div>
        </div>
      </div>
      <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted">{leader.reason}</p>
      <div className="mt-2 flex gap-4 text-[11px] text-muted">
        <span>
          封单 <span className="tabular text-ink">{formatAmount(leader.sealAmount)}</span>
        </span>
        {leader.firstSealTime ? (
          <span>
            首封 <span className="tabular text-ink">{leader.firstSealTime}</span>
          </span>
        ) : null}
      </div>
    </a>
  );
}

export function MarketLeadersBar({ leaders }: { leaders: MarketLeader[] }) {
  return (
    <section className="rounded-2xl border border-gold/25 bg-gradient-to-br from-gold/10 via-elev/80 to-elev/60 p-3 md:p-4">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-[11px] tracking-[0.18em] text-gold">MARKET LEADERS</p>
          <h2 className="text-lg font-semibold text-ink">今日全市场龙头</h2>
          <p className="text-xs text-muted">情绪资金自选 · 全市场涨停池按先封时间 → 连板 → 封单排出</p>
        </div>
      </div>
      {leaders.length ? (
        <div className="grid gap-2 md:grid-cols-3">
          {leaders.map((leader) => (
            <LeaderTile key={leader.code} leader={leader} />
          ))}
        </div>
      ) : (
        <p className="rounded-xl border border-dashed border-line bg-elev/50 px-4 py-6 text-center text-sm text-muted">
          盘中出现涨停后，这里会自动排出总龙头、龙二、龙三
        </p>
      )}
    </section>
  );
}
