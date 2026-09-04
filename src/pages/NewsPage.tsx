import { api } from "@/api/services";
import { Card, StateGate } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

export function NewsPage() {
  const { common } = useApp();
  const news = useAsync(() => api.news(0, common, 40), [common]);

  return (
    <Card title="最新消息">
      <StateGate loading={news.loading} error={news.error} empty={!news.data?.List?.length}>
        {(news.data?.List || []).map((item) => (
          <article className="news-item" key={item.ID}>
            <div className="live-meta">
              <span>{formatDateTime(item.Time)}</span>
              {item.StockName ? <span className="pill">{item.StockName} {item.StockID}</span> : null}
            </div>
            {item.URL ? (
              <a href={item.URL} target="_blank" rel="noreferrer">
                {item.Content}
              </a>
            ) : (
              <div>{item.Content}</div>
            )}
          </article>
        ))}
      </StateGate>
    </Card>
  );
}
