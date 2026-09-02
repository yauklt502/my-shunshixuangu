import { useState } from "react";
import { api } from "@/api/services";
import { Card, Kpi, Pct, StateGate, StockCell, Table, Tabs } from "@/components/ui";
import { fmtMoney, num } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

const BID_TABS = [
  { id: "0", label: "涨停委买", type: 4 },
  { id: "1", label: "撮合>2000万", type: 10 },
  { id: "2", label: "近期热门", type: 5 },
  { id: "3", label: "主力净额>1000万", type: 6 },
  { id: "4", label: "竞价砸盘", type: 5 },
];

export function AuctionPage() {
  const { date, today, common } = useApp();
  const [tab, setTab] = useState("0");
  const current = BID_TABS.find((t) => t.id === tab) || BID_TABS[0];

  const overview = useAsync(() => api.morningBidding(date, common), [date, common]);
  const nums = useAsync(() => api.morningBiddingNum(date, common), [date, common]);
  const list = useAsync(
    () => api.morningBiddingList(date, Number(current.id), current.type, common),
    [date, common, current.id, current.type],
  );
  const tail = useAsync(() => api.getWPQC(date, today, common), [date, today, common]);

  const info = overview.data?.info;
  const n = nums.data?.info || [];

  return (
    <>
      <div className="grid g-4">
        <Kpi label="今日竞价额" value={info?.tJJJE || "--"} meta={`昨日 ${info?.lJJJE || "--"}`} />
        <Kpi label="预测成交" value={info?.ycln || "--"} meta={`昨日 ${info?.lln || "--"}`} />
        <Kpi label="竞价上涨" value={info?.tSZ || "--"} meta={`昨日 ${info?.lSZ || "--"}`} tone="up" />
        <Kpi label="竞价下跌" value={info?.tXD || "--"} meta={`昨日 ${info?.lXD || "--"}`} tone="dn" />
      </div>
      <div className="grid g-4">
        <Kpi label="涨停委买" value={n[0] ?? "--"} />
        <Kpi label="撮合>2000万" value={n[1] ?? "--"} />
        <Kpi label="近期热门" value={n[2] ?? "--"} />
        <Kpi label="主力净额>1000万" value={n[3] ?? "--"} />
      </div>

      <Card title="竞价列表" extra={<Tabs value={tab} onChange={setTab} items={BID_TABS.map((t) => ({ id: t.id, label: t.label }))} />}>
        <StateGate loading={list.loading} error={list.error} empty={!list.data?.info?.length}>
          <Table
            rows={(list.data?.info || []).filter((r) => Array.isArray(r)) as unknown[][]}
            columns={[
              { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
              { key: "p", title: "实时涨幅", align: "right", render: (r) => <Pct value={r[3]} /> },
              { key: "jp", title: "竞价涨幅", align: "right", render: (r) => <Pct value={r[5]} /> },
              { key: "wb", title: "涨停委买", align: "right", render: (r) => fmtMoney(r[4]) },
              { key: "net", title: "竞价净额", align: "right", render: (r) => fmtMoney(r[6]) },
              { key: "amt", title: "竞价额", align: "right", render: (r) => fmtMoney(r[8]) },
              { key: "bk", title: "板块", render: (r) => String(r[11] || "") },
            ]}
          />
        </StateGate>
      </Card>

      <Card title="尾盘抢筹">
        <StateGate loading={tail.loading} error={tail.error} empty={!tail.data?.List?.length}>
          <Table
            rows={tail.data?.List || []}
            columns={[
              { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
              { key: "tag", title: "标签", render: (r) => <span className="pill">{String(r[2] || "")}</span> },
              { key: "bk", title: "板块", render: (r) => String(r[4] || "") },
              { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[5]} /> },
              { key: "qc", title: "抢筹金额", align: "right", render: (r) => fmtMoney(r[11]) },
              { key: "r", title: "抢筹幅度", align: "right", render: (r) => `${num(r[15]).toFixed(2)}%` },
              { key: "z", title: "占比", align: "right", render: (r) => String(r[16] ?? "") },
            ]}
          />
        </StateGate>
      </Card>
    </>
  );
}
