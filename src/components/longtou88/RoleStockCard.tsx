import {
  formatAmount,
  formatPercent,
  formatPrice,
  quoteUrl,
  signedClass,
} from "@/lib/format";
import type { RoleStock } from "@/lib/longtou88/types";

export function RoleStockCard({ stock }: { stock: RoleStock }) {
  const tone = signedClass(stock.changePercent);
  const wrap = stock.isLimitUp ? "zt-glow" : stock.isBroken ? "broken-glow" : "";

  return (
    <a
      href={quoteUrl(stock.market, stock.code)}
      target="_blank"
      rel="noreferrer"
      className={`block rounded-xl border border-line bg-elev-2/90 p-3 transition hover:border-gold/40 ${wrap}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-1.5">
            {stock.isLimitUp ? (
              <span className="rounded bg-up/15 px-1.5 py-0.5 text-[11px] text-up">涨停</span>
            ) : null}
            {stock.isBroken ? (
              <span className="rounded bg-warn/15 px-1.5 py-0.5 text-[11px] text-warn">炸板</span>
            ) : null}
            {stock.consecutiveBoards && stock.consecutiveBoards > 1 ? (
              <span className="text-[11px] text-gold">{stock.consecutiveBoards}连板</span>
            ) : null}
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <h3 className="text-base font-semibold text-up">{stock.name}</h3>
            <span className="font-mono text-xs text-muted">{stock.code}</span>
          </div>
        </div>
        <div className="text-right">
          <div
            className={`tabular text-lg font-semibold leading-none ${tone === "down" ? "text-down" : "text-up"}`}
          >
            {formatPercent(stock.changePercent)}
          </div>
          <div className="tabular mt-1 text-sm text-muted">{formatPrice(stock.price)}</div>
        </div>
      </div>
      <p className="mt-2 text-xs leading-5 text-muted">{stock.reason}</p>
      <dl className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-muted">
        <div>
          <dt>成交额</dt>
          <dd className="tabular text-ink">{formatAmount(stock.amount)}</dd>
        </div>
        <div>
          <dt>换手</dt>
          <dd className="tabular text-ink">
            {stock.turnoverRate === null ? "--" : `${stock.turnoverRate.toFixed(1)}%`}
          </dd>
        </div>
      </dl>
    </a>
  );
}
