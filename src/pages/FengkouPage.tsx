import { api } from "@/api/services";
import { Card, Pct, StateGate, StockCell, Table } from "@/components/ui";
import { fmtDateTime, fmtMoney, num } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

export function FengkouPage() {
  const { date, today, common } = useApp();
  const best = useAsync(() => api.fengKBest(date, today, common), [date, today, common]);
  const list = useAsync(() => api.fengKList(date, today, common), [date, today, common]);
  const plate = useAsync(() => api.fengKPlate(date, common), [date, common]);
  const maxAbs = Math.max(1, ...(plate.data?.List || []).map((r) => Math.abs(num(r[1]))));

  return (
    <div className="grid g-sidebar">
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Card title="最强风口" extra={<span className="faint">{best.data?.Tips || best.data?.Tip || ""}</span>}>
          <StateGate loading={best.loading} error={best.error} empty={!best.data?.List?.length}>
            <Table
              rows={best.data?.List || []}
              columns={[
                { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                { key: "q", title: "强度", align: "right", render: (r) => String(r[2]) },
                { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[4]} /> },
                { key: "m", title: "成交额", align: "right", render: (r) => fmtMoney(r[5]) },
                { key: "bk", title: "板块", render: (r) => String(r[10] || r[12] || "") },
                { key: "t", title: "时间", render: (r) => fmtDateTime(Number(r[11])) },
              ]}
            />
          </StateGate>
        </Card>
        <Card title="股票风口明细">
          <StateGate loading={list.loading} error={list.error} empty={!list.data?.List?.length}>
            <Table
              rows={list.data?.List || []}
              columns={[
                { key: "s", title: "股票", render: (r) => <StockCell code={r[0]} name={r[1]} /> },
                { key: "p", title: "涨幅", align: "right", render: (r) => <Pct value={r[3]} /> },
                { key: "m", title: "成交额", align: "right", render: (r) => fmtMoney(r[4]) },
                { key: "net", title: "净额", align: "right", render: (r) => fmtMoney(r[7]) },
                { key: "tag", title: "标签", render: (r) => String(r[10] || "") },
                { key: "bk", title: "概念", render: (r) => String(r[8] || r[11] || "") },
              ]}
            />
          </StateGate>
        </Card>
      </div>
      <Card title="概念风口">
        <StateGate loading={plate.loading} error={plate.error} empty={!plate.data?.List?.length}>
          {(plate.data?.List || []).map((row) => {
            const v = num(row[1]);
            const width = `${(Math.abs(v) / maxAbs) * 100}%`;
            return (
              <div className="feng-bar" key={String(row[0])}>
                <span>{row[0]}</span>
                <div className="bar">
                  <i style={{ width, background: v >= 0 ? "linear-gradient(90deg,#c4484e,#e8c36a)" : "var(--dn)" }} />
                </div>
                <b className={`mono ${v >= 0 ? "up" : "dn"}`}>{v.toFixed(1)}</b>
              </div>
            );
          })}
        </StateGate>
      </Card>
    </div>
  );
}
