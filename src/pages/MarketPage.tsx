import { useMemo } from "react";
import { api } from "@/api/services";
import { BoardLadder, Card, ErrorBox, Kpi, Pct, SentimentGauge, Spinner, StockCell, Table, VolumeChart } from "@/components/ui";
import { fmtMoney, fmtPct, num, pctClass } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

type Bundle = Awaited<ReturnType<typeof loadMarket>>;

async function loadMarket(date: string, today: string, common: ReturnType<typeof useApp>["common"]) {
  const [sentiment, capacity, zd, ladder, expr, weight, indices] = await Promise.all([
    api.changeStatistics(date, common),
    api.marketCapacity(date, common),
    api.marketStockZDNum(date, common),
    api.dailyLimitIndex(date, today, common),
    api.zhangTingExpression(date, common),
    api.weightPerformance(date, common),
    date === today ? api.refreshStockList(common) : Promise.resolve(null),
  ]);
  return { sentiment, capacity, zd, ladder, expr, weight, indices };
}

export function MarketPage() {
  const { date, today, common } = useApp();
  const { data, loading, error } = useAsync<Bundle>(() => loadMarket(date, today, common), [date, today, common]);

  const todayMood = data?.sentiment.info?.[0];
  const expr = data?.expr.info || [];
  const indices = data?.indices?.StockList || [];

  const volumeTone = num(data?.capacity.info.csbl) < 0 ? "dn" : "up";

  const weightRows = useMemo(() => {
    const sz = (data?.weight.info.SZ || []).map((row) => ({ side: "up" as const, row }));
    const xd = (data?.weight.info.XD || []).map((row) => ({ side: "dn" as const, row }));
    return [...sz, ...xd];
  }, [data]);

  if (loading) return <Spinner />;
  if (error) return <ErrorBox text={error} />;
  if (!data) return null;

  return (
    <>
      {indices.length > 0 && (
        <div className="grid g-4">
          {indices.map((idx) => (
            <div className="card idx-card" key={idx.StockID}>
              <div className="name">{idx.prod_name}</div>
              <div className={`px ${pctClass(idx.increase_rate)}`}>{Number(idx.last_px).toFixed(2)}</div>
              <div className="chg">
                <Pct value={idx.increase_rate} />
                <span className={pctClass(idx.increase_amount)}>
                  {num(idx.increase_amount) > 0 ? "+" : ""}
                  {Number(idx.increase_amount).toFixed(2)}
                </span>
                <span className="faint">{fmtMoney(idx.turnover)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid g-4">
        <Kpi label="情绪强度" value={todayMood?.strong ?? "--"} meta={todayMood?.Day} tone={num(todayMood?.strong) >= 75 ? "up" : num(todayMood?.strong) <= 25 ? "dn" : "flat"} />
        <Kpi label="涨停 / 跌停" value={`${data.zd.info.SJZT} / ${data.zd.info.SJDT}`} meta={`连板高度 ${todayMood?.lbgd || "--"}`} />
        <Kpi label="预测成交" value={data.capacity.info.ycln || fmtMoney(Number(data.capacity.info.last) * 10000)} meta={data.capacity.info.yclnstr} tone={volumeTone} />
        <Kpi label="大幅回撤" value={todayMood?.df_num ?? "--"} meta={`涨停家数 ${todayMood?.ztjs || expr[0] || "--"}`} />
      </div>

      <div className="grid g-sidebar">
        <Card title="两市量能" extra={<span className="faint">金线今日 / 蓝线昨日</span>}>
          <VolumeChart trends={data.capacity.info.trends} />
        </Card>
        <Card title="情绪温度">
          <div className="gauge-wrap">
            <SentimentGauge value={num(todayMood?.strong)} />
            <div className="tip">{data.sentiment.tip}</div>
          </div>
        </Card>
      </div>

      <div className="grid g-2">
        <Card title="涨停梯队">
          <BoardLadder counts={data.ladder.info || []} />
        </Card>
        <Card title="涨停表现">
          <div className="grid g-2">
            <Mini label="涨停家数" value={String(expr[0] ?? "--")} />
            <Mini label="最高板" value={`${expr[3] ?? "--"}板`} />
            <Mini label="2板晋级率" value={fmtPct(expr[4])} />
            <Mini label="破板率" value={fmtPct(expr[7])} />
            <Mini label="昨日涨停表现" value={fmtPct(expr[8])} />
            <Mini label="昨日连板表现" value={fmtPct(expr[9])} />
          </div>
          <p className="tip" style={{ marginTop: 12 }}>{String(expr[11] || "")}</p>
        </Card>
      </div>

      <div className="grid g-sidebar">
        <Card title="近期情绪">
          <Table
            rows={data.sentiment.info || []}
            columns={[
              { key: "Day", title: "日期" },
              { key: "strong", title: "情绪", align: "right", className: (r) => pctClass(num(r.strong) - 50), render: (r) => r.strong },
              { key: "ztjs", title: "涨停", align: "right" },
              { key: "lbgd", title: "高度", align: "right" },
              { key: "df_num", title: "回撤", align: "right" },
            ]}
          />
        </Card>
        <Card title="权重涨跌">
          <Table
            rows={weightRows}
            columns={[
              {
                key: "name",
                title: "板块",
                render: (r) => <span className={r.side === "up" ? "up" : "dn"}>{String(r.row[1])}</span>,
              },
              { key: "pct", title: "涨幅", align: "right", render: (r) => <Pct value={r.row[2]} /> },
              { key: "stock", title: "领涨/领跌", render: (r) => <StockCell code={r.row[3]} name={r.row[4]} /> },
              { key: "sp", title: "个股", align: "right", render: (r) => <Pct value={r.row[5]} /> },
            ]}
          />
        </Card>
      </div>
    </>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="faint" style={{ fontSize: 12 }}>{label}</div>
      <div className="mono" style={{ fontSize: 18, marginTop: 4 }}>{value}</div>
    </div>
  );
}
