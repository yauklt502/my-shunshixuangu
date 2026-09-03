import { useMemo, useState } from "react";
import { api } from "@/api/services";
import { Table } from "@/components/ui";
import { bidVolume, fmtVol, marketSessionDate, num, pctClass, str } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

const BID_TABS = [
  { id: "0", pill: "涨停委买", tab: "涨停委买", type: 4, tone: "up" },
  { id: "1", pill: "撮合>2000万", tab: "撮合>2000万", type: 10, tone: "mute" },
  { id: "2", pill: "热门股", tab: "热门股", type: 5, tone: "hot" },
  { id: "3", pill: "主力净额>1000万", tab: "主力净额", type: 6, tone: "hot" },
  { id: "4", pill: "砸盘", tab: "竞价砸盘", type: 5, tone: "dn" },
];

function codeKey(value: unknown) {
  return str(value).replace(/^(SH|SZ|BJ)/i, "").slice(-6);
}

function fmtHs(value: unknown) {
  const n = num(value, NaN);
  return Number.isFinite(n) ? `${n.toFixed(2)}%` : "--";
}

function fmtBidMoney(value: unknown) {
  const n = num(value, NaN);
  if (!Number.isFinite(n)) return "--";
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1e8) return `${sign}${(abs / 1e8).toFixed(1)}亿`;
  if (abs >= 1e4) return `${sign}${(abs / 1e4).toFixed(abs >= 1e6 ? 0 : 1)}万`;
  return `${sign}${abs.toFixed(0)}`;
}

function BidPct({ value }: { value: unknown }) {
  const n = num(value, NaN);
  if (!Number.isFinite(n)) return <span>--</span>;
  return <span className={pctClass(n)}>{n.toFixed(2)}%</span>;
}

export function AuctionPage() {
  const { date, today, holidays, common } = useApp();
  const [tab, setTab] = useState("0");
  const current = BID_TABS.find((item) => item.id === tab) || BID_TABS[0];
  const live = date === today || date === marketSessionDate(holidays);

  const overview = useAsync(() => api.morningBidding(date, common), [date, common]);
  const nums = useAsync(() => api.morningBiddingNum(date, common), [date, common]);
  const list = useAsync(
    () => api.morningBiddingList(date, live, Number(current.id), current.type, common),
    [date, live, common, current.id, current.type],
  );
  const tian = useAsync(() => api.getZhangTingTianTi(date, today, common), [date, today, common]);

  const info = overview.data?.info;
  const counts = nums.data?.info || [];
  const rows = ((list.loading ? [] : list.data?.info) || []).filter((r) => Array.isArray(r)) as unknown[][];

  const lianban = useMemo(() => {
    const map = new Map<string, number>();
    for (const row of tian.data?.StockList || []) {
      map.set(codeKey(row[0]), num(row[2]));
    }
    return map;
  }, [tian.data]);

  const columns = useMemo(
    () => [
      {
        key: "code",
        title: "代码",
        sortValue: (r: unknown[]) => str(r[0]),
        render: (r: unknown[]) => <span className="faint mono">{str(r[0])}</span>,
      },
      {
        key: "name",
        title: "名称",
        sortValue: (r: unknown[]) => str(r[1]),
        render: (r: unknown[]) => <b>{str(r[1])}</b>,
      },
      {
        key: "p",
        title: "当前涨幅",
        align: "right" as const,
        sortValue: (r: unknown[]) => num(r[3], NaN),
        render: (r: unknown[]) => <BidPct value={r[3]} />,
      },
      {
        key: "jp",
        title: "竞价涨幅",
        align: "right" as const,
        sortValue: (r: unknown[]) => num(r[5], NaN),
        render: (r: unknown[]) => {
          const boards = lianban.get(codeKey(r[0]));
          return (
            <div className="bid-jp">
              <BidPct value={r[5]} />
              {boards && boards >= 2 ? <span className="lianban">{boards}连板</span> : null}
            </div>
          );
        },
      },
      {
        key: "wb",
        title: "涨停委买",
        align: "right" as const,
        sortValue: (r: unknown[]) => num(r[4], NaN),
        render: (r: unknown[]) => <span className="up">{fmtBidMoney(r[4])}</span>,
      },
      {
        key: "amt",
        title: "竞价额",
        align: "right" as const,
        sortValue: (r: unknown[]) => num(r[8], 0) || num(r[10], 0),
        render: (r: unknown[]) => <span className="muted">{fmtBidMoney(num(r[8], 0) || num(r[10], 0))}</span>,
      },
      {
        key: "vol",
        title: "竞价量",
        align: "right" as const,
        sortValue: (r: unknown[]) => bidVolume(r),
        render: (r: unknown[]) => <span className="muted">{fmtVol(bidVolume(r))}</span>,
      },
      {
        key: "hs",
        title: "竞价换手",
        align: "right" as const,
        sortValue: (r: unknown[]) => num(r[7], NaN),
        render: (r: unknown[]) => <span className="muted">{fmtHs(r[7])}</span>,
      },
    ],
    [lianban],
  );

  return (
    <>
      <section className="card bid-panel">
        <div className="bid-head">
          <h3>竞价数据</h3>
          <span className="faint">
            ({date} · {counts[Number(tab)] ?? rows.length}只)
          </span>
        </div>

        <div className="bid-kpis">
          <div className="bid-kpi">
            <div className="k">竞价金额(今/昨)</div>
            <div className="v">
              {info?.tJJJE || "--"} <span className="split">/</span> {info?.lJJJE || "--"}
            </div>
          </div>
          <div className="bid-kpi">
            <div className="k">预测成交(今/昨)</div>
            <div className="v">
              {info?.ycln || "--"} <span className="split">/</span> {info?.lln || "--"}
            </div>
          </div>
          <div className="bid-kpi">
            <div className="k">上涨家数(今/昨)</div>
            <div className="v up">
              {info?.tSZ || "--"} <span className="split">/</span> {info?.lSZ || "--"}
            </div>
          </div>
          <div className="bid-kpi">
            <div className="k">下跌家数(今/昨)</div>
            <div className="v dn">
              {info?.tXD || "--"} <span className="split">/</span> {info?.lXD || "--"}
            </div>
          </div>
        </div>

        <div className="bid-cats">
          {BID_TABS.map((item, index) => (
            <button
              key={item.id}
              className={`bid-cat ${item.tone} ${tab === item.id ? "active" : ""}`}
              onClick={() => setTab(item.id)}
            >
              {item.pill} {counts[index] ?? "--"}
            </button>
          ))}
        </div>

        <div className="bid-tabs">
          {BID_TABS.map((item) => (
            <button
              key={item.id}
              className={`bid-tab ${tab === item.id ? "active" : ""}`}
              onClick={() => setTab(item.id)}
            >
              {item.tab}
            </button>
          ))}
        </div>

        <Table
          key={tab}
          rows={rows}
          columns={columns}
          loading={list.loading}
          error={list.error}
          emptyText="暂无数据"
        />
      </section>
    </>
  );
}
