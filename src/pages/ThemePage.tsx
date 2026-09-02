import { useState } from "react";
import { api } from "@/api/services";
import { Card, StateGate, StockCell, Table } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

export function ThemePage() {
  const { common } = useApp();
  const [q, setQ] = useState("算力");
  const [id, setId] = useState("261");
  const search = useAsync(() => api.themeSearch(q, common), [q, common]);
  const detail = useAsync(() => api.themeInfo(id, common), [id, common]);

  return (
    <div className="grid g-sidebar">
      <Card
        title="题材库搜索"
        extra={
          <form
            className="search"
            onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              setQ(String(fd.get("q") || "").trim());
            }}
          >
            <input name="q" defaultValue={q} placeholder="关键词，如 光、算力" />
            <button className="ghost-btn" type="submit">搜索</button>
          </form>
        }
      >
        <StateGate loading={search.loading} error={search.error} empty={!search.data?.List?.length && !search.data?.SList?.length}>
          <Table
            rows={search.data?.List || []}
            onRowClick={(r) => setId(r.ID)}
            columns={[
              { key: "Name", title: "题材" },
              { key: "ID", title: "ID" },
            ]}
          />
          <div style={{ height: 12 }} />
          {(search.data?.SList || []).map((item) => (
            <div key={item.ID} className="list-block">
              <div className="reason-hd">
                <b>{item.Name}</b>
                <button className="ghost-btn" onClick={() => setId(item.ID)}>查看</button>
              </div>
              <div className="tabs">
                {(item.LName || []).map((name) => (
                  <span className="pill" key={name}>{name}</span>
                ))}
              </div>
            </div>
          ))}
        </StateGate>
      </Card>

      <Card title={detail.data?.Name || "题材详情"}>
        <StateGate loading={detail.loading} error={detail.error}>
          <p className="tip">{detail.data?.BriefIntro}</p>
          {(detail.data?.Table || []).map((block) => (
            <div key={block.Level1.ID} className="list-block">
              <div className="reason-hd">
                <b>{block.Level1.Name}</b>
              </div>
              <Table
                rows={block.Level1.Stocks || []}
                columns={[
                  { key: "s", title: "股票", render: (r) => <StockCell code={r.StockID} name={r.prod_name} /> },
                  { key: "h", title: "热度", align: "right", render: (r) => String(r.Hot ?? "") },
                  { key: "r", title: "逻辑", render: (r) => r.Reason || "" },
                ]}
              />
            </div>
          ))}
          {!!detail.data?.StockList?.length && (
            <Table
              rows={detail.data.StockList}
              columns={[
                { key: "s", title: "关联股票", render: (r) => <StockCell code={r.StockID} name={r.prod_name} /> },
                { key: "h", title: "热度", align: "right", render: (r) => String(r.HotNum ?? "") },
                { key: "t", title: "标签", render: (r) => (r.Tag || []).map((t) => t.Name).join("、") },
              ]}
            />
          )}
        </StateGate>
      </Card>
    </div>
  );
}
