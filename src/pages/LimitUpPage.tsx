import { useState } from "react";
import { api } from "@/api/services";
import { Card, Pct, StateGate, StockCell, Table, Tabs } from "@/components/ui";
import { fmtHm, fmtMoney, num, unwrapList } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

const BOARDS = [
  { id: "1", label: "一板" },
  { id: "2", label: "二板" },
  { id: "3", label: "三板" },
  { id: "4", label: "四板" },
  { id: "5", label: "五板+" },
];

const BROKEN = [
  { id: "1", label: "今日破板" },
  { id: "2", label: "昨日一板" },
  { id: "3", label: "昨日二板" },
  { id: "4", label: "昨日三板" },
  { id: "5", label: "昨日四板+" },
];

export function LimitUpPage() {
  const { date, today, common } = useApp();
  const [tab, setTab] = useState("ladder");
  const [board, setBoard] = useState("1");
  const [broken, setBroken] = useState("1");

  const tian = useAsync(
    () => (tab === "ladder" ? api.getZhangTingTianTi(date, today, common) : Promise.resolve(null)),
    [tab, date, today, common],
  );
  const boards = useAsync(
    () => (tab === "boards" ? api.dailyLimitPerformance(date, today, Number(board), common) : Promise.resolve(null)),
    [tab, date, today, common, board],
  );
  const brokenQ = useAsync(
    () => (tab === "broken" ? api.dailyLimitPerformance2(date, today, Number(broken), common) : Promise.resolve(null)),
    [tab, date, today, common, broken],
  );
  const reasons = useAsync(
    () => (tab === "reason" ? api.getPlateInfo(date, common) : Promise.resolve(null)),
    [tab, date, common],
  );
  const highlights = useAsync(
    () => (tab === "light" ? api.getPMSL(date, today, common) : Promise.resolve(null)),
    [tab, date, today, common],
  );
  const drawdown = useAsync(
    () => (tab === "down" ? api.sharpWithdrawal(date, common) : Promise.resolve(null)),
    [tab, date, common],
  );

  return (
    <>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "ladder", label: "涨停天梯" },
          { id: "boards", label: "分板明细" },
          { id: "broken", label: "破板个股" },
          { id: "reason", label: "涨停原因" },
          { id: "light", label: "盘面亮点" },
          { id: "down", label: "大幅回撤" },
        ]}
      />

      {tab === "ladder" && (
        <Card title="涨停个股 / 主线板块">
          <StateGate loading={tian.loading} error={tian.error} empty={!tian.data?.StockList?.length}>
            <Table
              rows={tian.data?.StockList || []}
              rowKey={(r) => String(r[0])}
              columns={[
                { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                { key: "lb", title: "连板", align: "right", render: (r) => <b className="up">{String(r[2])}板</b> },
                { key: "t", title: "涨停时间", render: (r) => fmtHm(Number(r[3])) },
                { key: "p", title: "板块", render: (r) => String(r[5]) },
                { key: "n", title: "板块涨停", align: "right", render: (r) => String(r[8]) },
                { key: "m", title: "成交额", align: "right", render: (r) => fmtMoney(r[9]) },
              ]}
            />
            <div style={{ height: 16 }} />
            <Table
              rows={tian.data?.ZhuShuList || []}
              columns={[
                { key: "n", title: "主线", render: (r) => String(r[1]) },
                { key: "c", title: "代码", render: (r) => String(r[0]) },
                { key: "z", title: "涨停数", align: "right", render: (r) => String(r[2]) },
                { key: "m", title: "板块成交", align: "right", render: (r) => fmtMoney(r[3]) },
              ]}
            />
          </StateGate>
        </Card>
      )}

      {tab === "boards" && (
        <Card title="分板涨停" extra={<Tabs value={board} onChange={setBoard} items={BOARDS} />}>
          <StateGate loading={boards.loading} error={boards.error} empty={!unwrapList(boards.data?.info).length}>
            <Table
              rows={unwrapList(boards.data?.info)}
              rowKey={(r) => String(r[0])}
              columns={[
                { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                { key: "t", title: "涨停时间", render: (r) => fmtHm(Number(r[4])) },
                { key: "why", title: "原因", render: (r) => String(r[5] || "") },
                { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[22]} /> },
                { key: "px", title: "价格", align: "right", render: (r) => String(r[21] ?? "") },
                { key: "fd", title: "封单", align: "right", render: (r) => fmtMoney(r[6]) },
                { key: "to", title: "成交额", align: "right", render: (r) => fmtMoney(r[11]) },
                { key: "bk", title: "板块", render: (r) => String(r[12] || "") },
              ]}
            />
          </StateGate>
        </Card>
      )}

      {tab === "broken" && (
        <Card title="破板 / 掉队" extra={<Tabs value={broken} onChange={setBroken} items={BROKEN} />}>
          <StateGate loading={brokenQ.loading} error={brokenQ.error} empty={!unwrapList(brokenQ.data?.info).length}>
            <Table
              rows={unwrapList(brokenQ.data?.info)}
              rowKey={(r) => String(r[0])}
              columns={[
                { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                { key: "px", title: "价格", align: "right", render: (r) => String(r[4] ?? "") },
                { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[5]} /> },
                { key: "bk", title: "板块", render: (r) => String(r[6] || "") },
                { key: "net", title: "主力净额", align: "right", render: (r) => fmtMoney(r[7]) },
                { key: "to", title: "成交额", align: "right", render: (r) => fmtMoney(r[10]) },
              ]}
            />
          </StateGate>
        </Card>
      )}

      {tab === "reason" && (
        <Card title="涨停原因">
          <StateGate loading={reasons.loading} error={reasons.error} empty={!reasons.data?.list?.length}>
            {reasons.data?.nums && !Array.isArray(reasons.data.nums) && (
              <div className="grid g-4" style={{ marginBottom: 12 }}>
                <span className="pill">上涨 {reasons.data.nums.SZJS}</span>
                <span className="pill">下跌 {reasons.data.nums.XDJS}</span>
                <span className="pill up">涨停 {reasons.data.nums.ZT}</span>
                <span className="pill dn">跌停 {reasons.data.nums.DT}</span>
              </div>
            )}
            {(reasons.data?.list || []).map((group) => (
              <div className="list-block" key={group.ZSCode}>
                <div className="reason-hd">
                  <b>{group.ZSName}</b>
                  <span className="faint">{group.num} 只</span>
                </div>
                <Table
                  rows={group.StockList || []}
                  columns={[
                    { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                    { key: "lb", title: "板", render: (r) => String(r[9] || "") },
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

      {tab === "light" && (
        <Card title="盘面亮点">
          <StateGate loading={highlights.loading} error={highlights.error} empty={!highlights.data?.List?.length}>
            <Table
              rows={highlights.data?.List || []}
              columns={[
                { key: "t", title: "时间", render: (r) => fmtHm(r.TimeMin) },
                { key: "tag", title: "标签", render: (r) => <span className="pill gold">{r.TagName}</span> },
                { key: "zs", title: "板块", render: (r) => r.ZSName },
                {
                  key: "s",
                  title: "股票",
                  render: (r) => r.StockList?.map((s) => `${s[1]}(${s[0]})`).join("、"),
                },
                { key: "d", title: "说明", render: (r) => r.Detail },
              ]}
            />
          </StateGate>
        </Card>
      )}

      {tab === "down" && (
        <Card title="大幅回撤">
          <StateGate loading={drawdown.loading} error={drawdown.error} empty={!drawdown.data?.info?.length}>
            <Table
              rows={drawdown.data?.info || []}
              columns={[
                { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[2]} /> },
                { key: "d", title: "回撤", align: "right", render: (r) => <span className="dn">{num(r[3]).toFixed(2)}%</span> },
                { key: "px", title: "价格", align: "right", render: (r) => String(r[4]) },
              ]}
            />
          </StateGate>
        </Card>
      )}
    </>
  );
}
