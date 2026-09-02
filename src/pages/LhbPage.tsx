import { useState } from "react";
import { api, type Seat } from "@/api/services";
import { Card, Modal, Pct, StateGate, StockCell, Table, Tabs } from "@/components/ui";
import { fmtMoney, fmtYi, num } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

export function LhbPage() {
  const { date, today, common } = useApp();
  const [tab, setTab] = useState("list");
  const [stock, setStock] = useState<string | null>(null);
  const [gid, setGid] = useState("7");

  const list = useAsync(
    () => (tab === "list" ? api.lhbList(date, common) : Promise.resolve(null)),
    [tab, date, common],
  );
  const flow = useAsync(
    () => (tab === "flow" ? api.getYTFP(date, today, common) : Promise.resolve(null)),
    [tab, date, today, common],
  );
  const youzi = useAsync(
    () => (tab === "youzi" ? api.youZiDongXiang(date, common) : Promise.resolve(null)),
    [tab, date, common],
  );
  const seats = useAsync(
    () => (tab === "seat" ? api.groupInfo(gid, common) : Promise.resolve(null)),
    [tab, gid, common],
  );
  const detail = useAsync(() => (stock ? api.lhbDetail(date, stock, common) : Promise.resolve(null)), [date, stock, common]);

  return (
    <>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "list", label: "上榜个股" },
          { id: "flow", label: "游资机构动向" },
          { id: "youzi", label: "游资席位成交" },
          { id: "seat", label: "游资席位资料" },
        ]}
      />

      {tab === "list" && (
        <Card title={`龙虎榜 ${list.data?.Total ?? ""} 只`}>
          <StateGate loading={list.loading} error={list.error} empty={!list.data?.list?.length}>
            <Table
              rows={list.data?.list || []}
              onRowClick={(r) => setStock(r.ID)}
              rowKey={(r) => r.ID}
              columns={[
                { key: "s", title: "股票", render: (r) => <StockCell code={r.ID} name={r.Name} /> },
                { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r.IncreaseAmount} /> },
                { key: "b", title: "净买入", align: "right", render: (r) => <span className={num(r.BuyIn) >= 0 ? "up" : "dn"}>{fmtMoney(r.BuyIn)}</span> },
                { key: "t", title: "成交额", align: "right", render: (r) => fmtMoney(r.Turnover) },
                { key: "a", title: "振幅", align: "right", render: (r) => `${r.Amplitude}%` },
                { key: "h", title: "换手", align: "right", render: (r) => `${r.TurnoverRatio}%` },
                { key: "c", title: "流通", align: "right", render: (r) => fmtYi(r.CircPrice) },
                {
                  key: "d",
                  title: "标签",
                  render: (r) => (
                    <>
                      {r.D3 === "1" && <span className="pill gold">三日榜</span>}{" "}
                      {(list.data?.lb?.[r.ID] || 0) > 1 && <span className="pill">连上 {list.data?.lb?.[r.ID]}</span>}{" "}
                      {(list.data?.BIcon?.[r.ID] || []).slice(0, 2).map((x) => (
                        <span className="pill up" key={x}>{x}</span>
                      ))}
                    </>
                  ),
                },
              ]}
            />
          </StateGate>
        </Card>
      )}

      {tab === "flow" && (
        <Card title="游资 / 机构当日买卖">
          <StateGate loading={flow.loading} error={flow.error} empty={!flow.data?.List?.length}>
            {(flow.data?.List || []).map((item, index) => (
              <div className="list-block" key={`${item.BID}-${index}`}>
                <div className="reason-hd">
                  <b>{item.BName}</b>
                  <span className="faint">#{item.BID}</span>
                </div>
                <div className="grid g-2">
                  <MiniSide title="买入" rows={item.Buy || []} up />
                  <MiniSide title="卖出" rows={item.Sell || []} up={false} />
                </div>
              </div>
            ))}
          </StateGate>
        </Card>
      )}

      {tab === "youzi" && (
        <Card title="游资动向">
          <StateGate loading={youzi.loading} error={youzi.error} empty={!youzi.data?.DongXiang?.length}>
            {(youzi.data?.DongXiang || []).map((yz) => (
              <div className="list-block" key={yz.ID}>
                <div className="reason-hd">
                  <b>{yz.ShortName}</b>
                  <button className="ghost-btn" onClick={() => { setGid(String(yz.ID)); setTab("seat"); }}>席位资料</button>
                </div>
                <Table
                  rows={yz.List || []}
                  onRowClick={(r) => setStock(String(r.ID).padStart(6, "0"))}
                  columns={[
                    { key: "s", title: "股票", render: (r) => <StockCell code={r.ID} name={r.Name} /> },
                    { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r.IncreaseAmount} /> },
                    { key: "m", title: "金额", align: "right", render: (r) => fmtMoney(r.Money) },
                    { key: "d3", title: "三日榜", render: (r) => (r.D3 ? "是" : "") },
                  ]}
                />
              </div>
            ))}
          </StateGate>
        </Card>
      )}

      {tab === "seat" && (
        <Card
          title={seats.data?.ShortName || "游资席位"}
          extra={
            <input
              value={gid}
              onChange={(e) => setGid(e.target.value)}
              placeholder="GID"
              style={{ width: 80, height: 32, borderRadius: 8, border: "1px solid var(--line-strong)", background: "transparent", padding: "0 8px" }}
            />
          }
        >
          <StateGate loading={seats.loading} error={seats.error}>
            <p className="tip">{seats.data?.Info}</p>
            <Table
              rows={seats.data?.BusinessList || []}
              columns={[
                { key: "ID", title: "席位 ID" },
                { key: "Name", title: "营业部" },
              ]}
            />
          </StateGate>
        </Card>
      )}

      {stock && (
        <Modal title={`${detail.data?.Name || stock} 龙虎榜详情`} onClose={() => setStock(null)}>
          <div className="card-bd">
            <StateGate loading={detail.loading} error={detail.error}>
              {detail.data && (
                <>
                  <div className="grid g-4" style={{ marginBottom: 16 }}>
                    <Mini label="现价" value={detail.data.CurPrice} />
                    <Mini label="涨幅" value={detail.data.QuoteChange} />
                    <Mini label="净买入" value={fmtMoney(detail.data.BuyIn)} />
                    <Mini label="连上次数" value={String(detail.data.lbnum ?? "--")} />
                  </div>
                  {(detail.data.List || []).map((block, i) => (
                    <div key={i}>
                      <p className="muted">上榜原因：{(block.UpReason || []).join("、")}</p>
                      <div className="grid g-2">
                        <SeatTable title={`买入 ${fmtMoney(block.BuyTotal)}`} rows={block.BuyList || []} />
                        <SeatTable title={`卖出 ${fmtMoney(block.SellTotal)}`} rows={block.SellList || []} />
                      </div>
                    </div>
                  ))}
                </>
              )}
            </StateGate>
          </div>
        </Modal>
      )}
    </>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="faint">{label}</div>
      <div className="mono" style={{ fontSize: 18 }}>{value}</div>
    </div>
  );
}

function MiniSide({
  title,
  rows,
  up,
}: {
  title: string;
  rows: Array<{ Sto: string; StoN: string; Money: number; Three: number }>;
  up: boolean;
}) {
  return (
    <div>
      <div className={up ? "up" : "dn"} style={{ marginBottom: 6 }}>{title}</div>
      <Table
        rows={rows}
        columns={[
          { key: "s", title: "股票", render: (r) => <StockCell code={r.Sto} name={r.StoN} /> },
          { key: "m", title: "金额", align: "right", render: (r) => fmtMoney(r.Money) },
          { key: "t", title: "三日", render: (r) => (r.Three ? "是" : "") },
        ]}
      />
    </div>
  );
}

function SeatTable({ title, rows }: { title: string; rows: Seat[] }) {
  return (
    <Card title={title}>
      <Table
        rows={rows}
        columns={[
          { key: "Name", title: "席位" },
          { key: "b", title: "买", align: "right", render: (r) => fmtMoney(r.Buy) },
          { key: "s", title: "卖", align: "right", render: (r) => fmtMoney(r.Sell) },
          { key: "g", title: "标签", render: (r) => (r.GroupIcon || []).join(" ") },
        ]}
      />
    </Card>
  );
}
