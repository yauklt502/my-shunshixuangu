import { useMemo } from "react";
import { api } from "@/api/services";
import { Table } from "@/components/ui";
import { fmtMoney, num, pctClass, str } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

function BidPct({ value }: { value: unknown }) {
  const n = num(value, NaN);
  if (!Number.isFinite(n)) return <span>--</span>;
  return <span className={pctClass(n)}>{n.toFixed(2)}%</span>;
}

export function GrabPage() {
  const { date, today, common } = useApp();
  const tail = useAsync(() => api.getWPQC(date, today, common), [date, today, common]);
  const rows = (tail.loading ? [] : tail.data?.List) || [];

  const stats = useMemo(() => {
    const amount = rows.reduce((sum, row) => sum + num(row[11]), 0);
    const youzi = rows.filter((row) => str(row[2]).includes("游资")).length;
    const jigou = rows.filter((row) => str(row[2]).includes("机构")).length;
    return { amount, youzi, jigou };
  }, [rows]);

  return (
    <section className="card bid-panel">
      <div className="bid-head">
        <h3>尾盘抢筹</h3>
        <span className="faint">
          ({date} · {rows.length}只)
        </span>
      </div>

      <div className="bid-kpis">
        <div className="bid-kpi">
          <div className="k">抢筹只数</div>
          <div className="v">{tail.loading ? "--" : rows.length}</div>
        </div>
        <div className="bid-kpi">
          <div className="k">抢筹总额</div>
          <div className="v up">{tail.loading ? "--" : fmtMoney(stats.amount)}</div>
        </div>
        <div className="bid-kpi">
          <div className="k">游资</div>
          <div className="v">{tail.loading ? "--" : stats.youzi}</div>
        </div>
        <div className="bid-kpi">
          <div className="k">机构</div>
          <div className="v">{tail.loading ? "--" : stats.jigou}</div>
        </div>
      </div>

      <Table
        rows={rows}
        loading={tail.loading}
        error={tail.error}
        emptyText="暂无尾盘抢筹数据"
        columns={[
          { key: "code", title: "代码", sortValue: (r) => str(r[0]), render: (r) => <span className="faint mono">{str(r[0])}</span> },
          { key: "name", title: "名称", sortValue: (r) => str(r[1]), render: (r) => <b>{str(r[1])}</b> },
          { key: "tag", title: "标签", sortValue: (r) => str(r[2]), render: (r) => <span className="pill">{str(r[2]) || "--"}</span> },
          { key: "bk", title: "板块", sortValue: (r) => str(r[4]), render: (r) => str(r[4]) || "--" },
          { key: "p", title: "涨幅", align: "right", sortValue: (r) => num(r[5], NaN), render: (r) => <BidPct value={r[5]} /> },
          { key: "amt", title: "成交额", align: "right", sortValue: (r) => num(r[6], NaN), render: (r) => <span className="muted">{fmtMoney(r[6])}</span> },
          { key: "net", title: "主力净额", align: "right", sortValue: (r) => num(r[10], NaN), render: (r) => <span className={pctClass(r[10])}>{fmtMoney(r[10])}</span> },
          { key: "qc", title: "抢筹金额", align: "right", sortValue: (r) => num(r[11], NaN), render: (r) => <span className="up">{fmtMoney(r[11])}</span> },
          { key: "r", title: "抢筹幅度", align: "right", sortValue: (r) => num(r[15], NaN), render: (r) => `${num(r[15]).toFixed(2)}%` },
          { key: "z", title: "占比", align: "right", sortValue: (r) => num(r[16], NaN), render: (r) => String(r[16] ?? "--") },
        ]}
      />
    </section>
  );
}
