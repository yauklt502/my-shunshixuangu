import { beijingClock, formatYmd } from "@/lib/format";
import type { WatchEvent } from "@/lib/types";

const KIND_CLASS: Record<WatchEvent["kind"], string> = {
  封板: "text-up",
  回封: "text-gold",
  开板: "text-warn",
  晋级: "text-gold",
  板块轮换: "text-silver",
};

export function EventFeed({
  events,
  tradeDate,
}: {
  events: WatchEvent[];
  tradeDate: string;
}) {
  return (
    <section className="rounded-2xl border border-line bg-elev/80 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-medium text-ink">盘中异动</h2>
        <span className="text-[11px] text-muted">交易日 {formatYmd(tradeDate)}</span>
      </div>
      {events.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted">
          盯盘刷新后，龙一龙二开板、回封、连板晋级会记在这里。
        </p>
      ) : (
        <ol className="max-h-40 space-y-1.5 overflow-auto pr-1">
          {events.map((event) => (
            <li
              key={event.id}
              className="flex items-start justify-between gap-3 rounded-lg bg-elev-2 px-2.5 py-1.5 text-xs"
            >
              <div>
                <span className={`mr-2 font-medium ${KIND_CLASS[event.kind]}`}>{event.kind}</span>
                <span className="text-ink">
                  {event.stockName}
                  <span className="ml-1 text-muted">{event.stockCode}</span>
                </span>
                <p className="mt-0.5 text-muted">
                  {event.sectorName} · {event.detail}
                </p>
              </div>
              <time className="shrink-0 tabular text-muted">{beijingClock(new Date(event.at))}</time>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
