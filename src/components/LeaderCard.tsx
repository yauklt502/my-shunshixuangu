import { Sparkline } from "@/components/Sparkline";
import {
  formatAmount,
  formatPercent,
  formatPrice,
  quoteUrl,
  signedClass,
} from "@/lib/format";
import type { RankedLeader } from "@/lib/types";

const RANK_STYLE: Record<RankedLeader["rank"], string> = {
  龙一: "bg-gold/15 text-gold border-gold/40",
  龙二: "bg-silver/10 text-silver border-silver/30",
  龙三: "bg-bronze/15 text-bronze border-bronze/35",
};

export function LeaderCard({ leader }: { leader: RankedLeader }) {
  const tone = signedClass(leader.changePercent);
  const wrap = leader.isLimitUp ? "zt-glow" : leader.isBroken ? "broken-glow" : "";

  return (
    <a
      href={quoteUrl(leader.market, leader.code)}
      target="_blank"
      rel="noreferrer"
      className={`block rounded-xl border border-line bg-elev-2/90 p-3 transition hover:border-gold/40 ${wrap}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${RANK_STYLE[leader.rank]}`}
            >
              {leader.rank}
            </span>
            {leader.isLimitUp ? (
              <span className="rounded bg-up/15 px-1.5 py-0.5 text-[11px] text-up">涨停</span>
            ) : null}
            {leader.isBroken ? (
              <span className="rounded bg-warn/15 px-1.5 py-0.5 text-[11px] text-warn">炸板</span>
            ) : null}
            {leader.consecutiveBoards && leader.consecutiveBoards > 1 ? (
              <span className="text-[11px] text-gold">{leader.consecutiveBoards}连板</span>
            ) : null}
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <h3 className="text-base font-semibold text-ink">{leader.name}</h3>
            <span className="font-mono text-xs text-muted">{leader.code}</span>
          </div>
        </div>
        <div className="text-right">
          <div className={`tabular text-lg font-semibold leading-none ${tone === "down" ? "text-down" : "text-up"}`}>
            {formatPercent(leader.changePercent)}
          </div>
          <div className="tabular mt-1 text-sm text-muted">{formatPrice(leader.price)}</div>
        </div>
      </div>
      <p className="mt-2 text-xs leading-5 text-muted">{leader.reason}</p>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-[11px] text-muted">
        <div>
          <dt>成交额</dt>
          <dd className="tabular text-ink">{formatAmount(leader.amount)}</dd>
        </div>
        <div>
          <dt>换手</dt>
          <dd className="tabular text-ink">
            {leader.turnoverRate === null ? "--" : `${leader.turnoverRate.toFixed(1)}%`}
          </dd>
        </div>
        <div>
          <dt>{leader.isLimitUp ? "封单" : "主力净流"}</dt>
          <dd className="tabular text-ink">
            {formatAmount(leader.isLimitUp ? leader.sealAmount : leader.mainNetInflow)}
          </dd>
        </div>
      </dl>
      <Sparkline className="mt-2" points={leader.trend} tone={tone} />
    </a>
  );
}
