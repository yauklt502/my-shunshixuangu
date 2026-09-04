import { api } from "@/api/services";
import { Card, StateGate } from "@/components/ui";
import { formatDateTime, fmtPct } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/state";

export function LivePage() {
  const { date, today, common } = useApp();
  const live = useAsync(() => api.zhiBo(date, today, common), [date, today, common]);

  return (
    <Card title="大盘直播" extra={<span className="faint">{live.data?.Notice || live.data?.date || ""}</span>}>
      <StateGate loading={live.loading} error={live.error} empty={!live.data?.List?.length}>
        {(live.data?.List || []).map((item, index) => (
          <article className="live-item" key={`${item.ID}-${index}`}>
            <div className="live-meta">
              <b>{item.UserName || "直播"}</b>
              <span>{formatDateTime(item.Time)}</span>
            </div>
            <p>{item.Comment}</p>
            {!!item.Stock?.length && (
              <div className="tabs" style={{ marginTop: 8 }}>
                {item.Stock.map((s) => (
                  <span className="pill" key={s[0]}>
                    {s[1]} {s[2] !== undefined ? fmtPct(s[2]) : ""}
                  </span>
                ))}
              </div>
            )}
            {item.ShareData?.ZDTJ_info && (
              <div className="tabs" style={{ marginTop: 8 }}>
                <span className="pill up">涨停 {item.ShareData.ZDTJ_info.SJZT || item.ShareData.ZDTJ_info.ZT}</span>
                <span className="pill dn">跌停 {item.ShareData.ZDTJ_info.SJDT || item.ShareData.ZDTJ_info.DT}</span>
                <span className="pill">上涨 {item.ShareData.ZDTJ_info.SZJS}</span>
                <span className="pill">下跌 {item.ShareData.ZDTJ_info.XDJS}</span>
              </div>
            )}
          </article>
        ))}
      </StateGate>
    </Card>
  );
}
