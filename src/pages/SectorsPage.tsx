import { useState } from "react";
import { api } from "@/api/services";
import { Card, Modal, Pct, StateGate, StockCell, Table, Tabs } from "@/components/ui";
import { fmtHm, fmtMoney, fmtPct, num } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

const rankCols = [
  { key: "n", title: "板块", render: (r: unknown[]) => String(r[1]) },
  { key: "str", title: "强度", align: "right" as const, render: (r: unknown[]) => String(r[2]) },
  { key: "p", title: "涨幅", align: "right" as const, render: (r: unknown[]) => <Pct value={r[3]} /> },
  { key: "s", title: "涨速", align: "right" as const, render: (r: unknown[]) => <Pct value={r[4]} /> },
  { key: "m", title: "成交额", align: "right" as const, render: (r: unknown[]) => fmtMoney(r[5]) },
  { key: "net", title: "主力净额", align: "right" as const, render: (r: unknown[]) => fmtMoney(r[6]) },
  { key: "lb", title: "量比", align: "right" as const, render: (r: unknown[]) => num(r[9]).toFixed(2) },
];

export function SectorsPage() {
  const { date, today, common } = useApp();
  const [tab, setTab] = useState("strength");
  const [code, setCode] = useState("801807");
  const [picked, setPicked] = useState<{ code: string; name: string } | null>(null);

  const strength = useAsync(
    () => (tab === "strength" ? api.realRankingInfo(date, today, 1, 7, common) : Promise.resolve(null)),
    [tab, date, today, common],
  );
  const industry = useAsync(
    () => (tab === "industry" ? api.realRankingInfo(date, today, 2, 4, common) : Promise.resolve(null)),
    [tab, date, today, common],
  );
  const region = useAsync(
    () => (tab === "region" ? api.realRankingInfo(date, today, 2, 6, common) : Promise.resolve(null)),
    [tab, date, today, common],
  );
  const bid = useAsync(
    () => (tab === "bid" ? api.getBKJJ(date, today, common) : Promise.resolve(null)),
    [tab, date, today, common],
  );
  const history = useAsync(
    () => (tab === "hist" ? api.getDatePlate(code, common) : Promise.resolve(null)),
    [tab, code, common],
  );
  const bidStocks = useAsync(
    () => (picked ? api.getBKJJBL(date, today, picked.code, common) : Promise.resolve(null)),
    [date, today, common, picked?.code],
  );

  return (
    <>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "strength", label: "板块强度" },
          { id: "industry", label: "行业涨幅" },
          { id: "region", label: "地区涨幅" },
          { id: "bid", label: "板块竞价" },
          { id: "hist", label: "板块涨停历史" },
        ]}
      />

      {tab === "strength" && (
        <Card title="按强度排序">
          <StateGate loading={strength.loading} error={strength.error} empty={!strength.data?.list?.length}>
            <Table rows={strength.data?.list || []} columns={rankCols} onRowClick={(r) => setCode(String(r[0]))} />
          </StateGate>
        </Card>
      )}
      {tab === "industry" && (
        <Card title="行业">
          <StateGate loading={industry.loading} error={industry.error} empty={!industry.data?.list?.length}>
            <Table rows={industry.data?.list || []} columns={rankCols} />
          </StateGate>
        </Card>
      )}
      {tab === "region" && (
        <Card title="地区">
          <StateGate loading={region.loading} error={region.error} empty={!region.data?.list?.length}>
            <Table rows={region.data?.list || []} columns={rankCols} />
          </StateGate>
        </Card>
      )}
      {tab === "bid" && (
        <>
          <BidList title="今日新增异动" rows={bid.data?.List1 || []} loading={bid.loading} error={bid.error} onPick={setPicked} />
          <BidList title="昨日爆发延续" rows={bid.data?.List2 || []} loading={false} error={null} onPick={setPicked} />
          <BidList title="其他异动" rows={bid.data?.List3 || []} loading={false} error={null} onPick={setPicked} />
        </>
      )}
      {tab === "hist" && (
        <Card
          title={`涨停历史 · ${history.data?.ZSName || code}`}
          extra={
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="板块代码 如 801807"
              style={{ width: 140, height: 32, borderRadius: 8, border: "1px solid var(--line-strong)", background: "transparent", padding: "0 8px" }}
            />
          }
        >
          <StateGate loading={history.loading} error={history.error} empty={!history.data?.list?.length}>
            {(history.data?.list || []).map((day) => (
              <div className="list-block" key={day.Date}>
                <div className="reason-hd">
                  <b>{day.Date}</b>
                  <span className="faint">{day.num} 只涨停</span>
                </div>
                <Table
                  rows={day.StockList || []}
                  columns={[
                    { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                    { key: "lb", title: "状态", render: (r) => String(r[9] || "") },
                    { key: "t", title: "时间", render: (r) => fmtHm(Number(r[6])) },
                    { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[14]} /> },
                    { key: "why", title: "原因", render: (r) => String(r[16] || "") },
                  ]}
                />
              </div>
            ))}
          </StateGate>
        </Card>
      )}

      {picked && (
        <Modal title={`${picked.name} 竞价个股`} onClose={() => setPicked(null)}>
          <div className="card-bd">
            <StateGate loading={bidStocks.loading} error={bidStocks.error} empty={!bidStocks.data?.List?.length}>
              <Table
                rows={bidStocks.data?.List || []}
                columns={[
                  { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                  { key: "px", title: "现价", align: "right", render: (r) => String(r[2]) },
                  { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[3]} /> },
                  { key: "lb", title: "竞价量比", align: "right", render: (r) => String(r[4]) },
                  { key: "m", title: "竞价额", align: "right", render: (r) => fmtMoney(r[5]) },
                  { key: "jp", title: "竞价涨幅", align: "right", render: (r) => fmtPct(r[6]) },
                ]}
              />
            </StateGate>
          </div>
        </Modal>
      )}
    </>
  );
}

function BidList({
  title,
  rows,
  loading,
  error,
  onPick,
}: {
  title: string;
  rows: unknown[][];
  loading: boolean;
  error: string | null;
  onPick: (v: { code: string; name: string }) => void;
}) {
  return (
    <Card title={title}>
      <StateGate loading={loading} error={error} empty={!rows.length}>
        <Table
          rows={rows}
          onRowClick={(r) => onPick({ code: String(r[0]), name: String(r[1]) })}
          columns={[
            { key: "n", title: "板块", render: (r) => String(r[1]) },
            { key: "x", title: "爆量倍数", align: "right", render: (r) => String(r[2]) },
            { key: "m", title: "异动金额", align: "right", render: (r) => fmtMoney(r[3]) },
            { key: "net", title: "主力净额", align: "right", render: (r) => fmtMoney(r[5]) },
          ]}
        />
      </StateGate>
    </Card>
  );
}
