import {
  formatAmount,
  formatPercent,
  formatPrice,
  quoteUrl,
  signedClass,
} from "@/lib/format";
import { CRITERION_HINTS, TREND_CRITERIA, type TrendLeaderStock } from "@/lib/qushi-longtou/types";

export function TrendLeaderCard({ leader }: { leader: TrendLeaderStock }) {
  const tone = signedClass(leader.changePercent);

  return (
    <a
      href={quoteUrl(leader.market, leader.code)}
      target="_blank"
      rel="noreferrer"
      className="block rounded-xl border border-line bg-elev-2/90 p-3 transition hover:border-gold/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="mb-1.5 inline-flex rounded-md border border-gold/40 bg-gold/10 px-1.5 py-0.5 text-[11px] text-gold">
            趋势分 {leader.score}/5
          </div>
          <div className="flex items-baseline gap-2">
            <h3 className="text-base font-semibold text-up">{leader.name}</h3>
            <span className="font-mono text-xs text-muted">{leader.code}</span>
          </div>
        </div>
        <div className="text-right">
          <div
            className={`tabular text-lg font-semibold leading-none ${tone === "down" ? "text-down" : "text-up"}`}
          >
            {formatPercent(leader.changePercent)}
          </div>
          <div className="tabular mt-1 text-sm text-muted">{formatPrice(leader.price)}</div>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap gap-1">
        {TREND_CRITERIA.map((key) => (
          <span
            key={key}
            title={CRITERION_HINTS[key]}
            className={`rounded px-1.5 py-0.5 text-[10px] ${
              leader.checks[key]
                ? "bg-down/15 text-down"
                : "bg-elev text-muted line-through decoration-muted/50"
            }`}
          >
            {key}
          </span>
        ))}
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
          <dt>MA5</dt>
          <dd className="tabular text-ink">
            {leader.ma5 === null ? "--" : leader.ma5.toFixed(2)}
          </dd>
        </div>
      </dl>
    </a>
  );
}
