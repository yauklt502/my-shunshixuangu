import { useMemo, useState } from "react";
import { api } from "@/api/services";
import { Card, Pct, StateGate, StockCell, Table, Tabs } from "@/components/ui";
import { addDays, fmtMoney, fmtPct } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

export function StocksPage() {
  const { date, today, common } = useApp();
  const [tab, setTab] = useState("plate");
  const [code, setCode] = useState("002580");
  const start = useMemo(() => addDays(date, -7), [date]);

  const plate = useAsync(
    () => (tab === "plate" ? api.getStockIDPlate(code, common) : Promise.resolve(null)),
    [tab, code, common],
  );
  const plate2 = useAsync(
    () => (tab === "plate" ? api.getFeaturedSection(code, common) : Promise.resolve(null)),
    [tab, code, common],
  );
  const highs = useAsync(
    () => (tab === "high" ? api.groupStockHigh(date, today, common) : Promise.resolve(null)),
    [tab, date, today, common],
  );
  const zs = useAsync(
    () => (tab === "range" ? api.interviewsByZS(start, date, today, common) : Promise.resolve(null)),
    [tab, start, date, today, common],
  );
  const stocks = useAsync(
    () => (tab === "range" ? api.interviewsByStock(start, date, today, common) : Promise.resolve(null)),
    [tab, start, date, today, common],
  );
  const replay = useAsync(
    () => (tab === "replay" ? api.replayList(common) : Promise.resolve(null)),
    [tab, common],
  );
  const trend = useAsync(
    () => (tab === "high" ? api.newHighTrend("ALL", common) : Promise.resolve(null)),
    [tab, common],
  );

  return (
    <>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "plate", label: "个股板块" },
          { id: "high", label: "百日新高" },
          { id: "range", label: "区间统计" },
          { id: "replay", label: "复盘榜" },
        ]}
      />

      {tab === "plate" && (
        <Card
          title="所属板块"
          extra={
            <form
              className="search"
              onSubmit={(e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                setCode(String(fd.get("code") || "").trim());
              }}
            >
              <input name="code" defaultValue={code} placeholder="股票代码" />
              <button className="ghost-btn" type="submit">查询</button>
            </form>
          }
        >
          <StateGate loading={plate.loading} error={plate.error} empty={!plate.data?.List?.length}>
            <Table
              rows={plate.data?.List || []}
              columns={[
                { key: "c", title: "代码", render: (r) => String(r[0]) },
                { key: "n", title: "板块", render: (r) => String(r[1]) },
                { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[2]} /> },
              ]}
            />
          </StateGate>
          <div style={{ height: 16 }} />
          <h3 className="muted">板块龙头</h3>
          <StateGate loading={plate2.loading} error={plate2.error} empty={!plate2.data?.info?.length}>
            <Table
              rows={plate2.data?.info || []}
              columns={[
                { key: "n", title: "板块", render: (r) => String(r[1]) },
                { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[2]} /> },
                { key: "l", title: "龙头", render: (r) => <StockCell code={r[3]} name={r[4]} /> },
                { key: "lp", title: "龙头涨幅", align: "right", render: (r) => <Pct value={r[5]} /> },
              ]}
            />
          </StateGate>
        </Card>
      )}

      {tab === "high" && (
        <>
          <Card title="新高趋势（全市场）">
            <StateGate loading={trend.loading} error={trend.error} empty={!trend.data?.x?.length}>
              <Table
                rows={(trend.data?.x || []).slice(-12).reverse().map((row) => row.split("_"))}
                columns={[
                  { key: "0", title: "日期", render: (r) => `${r[0].slice(0, 4)}-${r[0].slice(4, 6)}-${r[0].slice(6, 8)}` },
                  { key: "1", title: "累计新高", align: "right" },
                  { key: "2", title: "当日新增", align: "right" },
                ]}
              />
            </StateGate>
          </Card>
          <Card title="百日新高（按板块）">
            <StateGate loading={highs.loading} error={highs.error} empty={!highs.data?.GroupList?.length}>
              {(highs.data?.GroupList || []).map((g) => (
                <div className="list-block" key={g.GroupID}>
                  <div className="reason-hd">
                    <b>{g.GroupName}</b>
                    <span className="faint">{g.List?.length || 0} 只</span>
                  </div>
                  <Table
                    rows={g.List || []}
                    columns={[
                      { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                      { key: "px", title: "价格", align: "right", render: (r) => String(r[2]) },
                      { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[3]} /> },
                      { key: "m", title: "成交额", align: "right", render: (r) => fmtMoney(r[5]) },
                      { key: "new", title: "新增", render: (r) => (Number(r[11]) === 1 ? "是" : "") },
                    ]}
                  />
                </div>
              ))}
            </StateGate>
          </Card>
        </>
      )}

      {tab === "range" && (
        <>
          <Card title={`板块区间 ${start} ~ ${date}`}>
            <StateGate loading={zs.loading} error={zs.error} empty={!zs.data?.List?.length}>
              <Table
                rows={zs.data?.List || []}
                columns={[
                  { key: "n", title: "板块", render: (r) => String(r[1]) },
                  { key: "p", title: "区间涨幅", align: "right", render: (r) => <Pct value={r[2]} /> },
                  { key: "net", title: "净额", align: "right", render: (r) => fmtMoney(r[5]) },
                  { key: "m", title: "成交额", align: "right", render: (r) => fmtMoney(r[6]) },
                  { key: "d", title: "净流入天数", align: "right", render: (r) => String(r[8]) },
                  { key: "q", title: "区间强度", align: "right", render: (r) => String(r[11]) },
                ]}
              />
            </StateGate>
          </Card>
          <Card title={`个股区间 ${start} ~ ${date}`}>
            <StateGate loading={stocks.loading} error={stocks.error} empty={!stocks.data?.List?.length}>
              <Table
                rows={stocks.data?.List || []}
                columns={[
                  { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                  { key: "px", title: "现价", align: "right", render: (r) => String(r[2]) },
                  { key: "p", title: "区间涨幅", align: "right", render: (r) => fmtPct(r[3]) },
                  { key: "net", title: "净额", align: "right", render: (r) => fmtMoney(r[6]) },
                  { key: "h", title: "换手", align: "right", render: (r) => fmtPct(r[7]) },
                  { key: "bk", title: "板块", render: (r) => String(r[10] || "") },
                ]}
              />
            </StateGate>
          </Card>
        </>
      )}

      {tab === "replay" && (
        <Card title="复盘推荐代码">
          <StateGate loading={replay.loading} error={replay.error} empty={!replay.data?.List?.length}>
            <div className="tabs">
              {(replay.data?.List || []).map((id) => (
                <button key={id} className="tab" onClick={() => { setCode(id); setTab("plate"); }}>
                  {id}
                </button>
              ))}
            </div>
          </StateGate>
        </Card>
      )}
    </>
  );
}
