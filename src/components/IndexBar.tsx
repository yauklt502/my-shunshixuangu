import { formatAmount, formatPercent, formatPrice, signedClass } from "@/lib/format";
import type { IndexQuote } from "@/lib/types";

function toneClass(value: number | null): string {
  const tone = signedClass(value);
  if (tone === "up") return "text-up";
  if (tone === "down") return "text-down";
  return "text-muted";
}

export function IndexBar({
  indices,
  ztCount,
  zbCount,
}: {
  indices: IndexQuote[];
  ztCount: number;
  zbCount: number;
}) {
  return (
    <section className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
      {indices.map((item) => (
        <article
          key={item.code}
          className="rounded-xl border border-line bg-elev/80 px-3 py-2.5 backdrop-blur"
        >
          <div className="flex items-center justify-between text-xs text-muted">
            <span>{item.name}</span>
            <span>
              涨{item.upCount ?? "--"} / 跌{item.downCount ?? "--"}
            </span>
          </div>
          <div className="mt-1 flex items-end justify-between gap-2">
            <strong className={`tabular text-xl leading-none ${toneClass(item.changePercent)}`}>
              {formatPrice(item.price)}
            </strong>
            <span className={`tabular text-sm ${toneClass(item.changePercent)}`}>
              {formatPercent(item.changePercent)}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-muted">成交 {formatAmount(item.amount, 1)}</p>
        </article>
      ))}
      <article className="rounded-xl border border-line bg-elev/80 px-3 py-2.5">
        <div className="text-xs text-muted">涨停 / 炸板</div>
        <div className="mt-1 flex items-end gap-3">
          <strong className="tabular text-xl leading-none text-up">{ztCount}</strong>
          <span className="text-sm text-muted">/</span>
          <strong className="tabular text-xl leading-none text-warn">{zbCount}</strong>
        </div>
        <p className="mt-1 text-[11px] text-muted">全市场情绪，辅助判断板块成色</p>
      </article>
    </section>
  );
}
