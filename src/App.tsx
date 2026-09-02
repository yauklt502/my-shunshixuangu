import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AppProvider, useApp } from "@/state";
import { chinaDate, formatClock, lastTradingDay, shiftTradingDay } from "@/lib/format";
import { Modal } from "@/components/ui";
import { MarketPage } from "@/pages/MarketPage";
import { LimitUpPage } from "@/pages/LimitUpPage";
import { SectorsPage } from "@/pages/SectorsPage";
import { LhbPage } from "@/pages/LhbPage";
import { AuctionPage } from "@/pages/AuctionPage";
import { StocksPage } from "@/pages/StocksPage";
import { FengkouPage } from "@/pages/FengkouPage";
import { ThemePage } from "@/pages/ThemePage";
import { LivePage } from "@/pages/LivePage";
import { NewsPage } from "@/pages/NewsPage";

const NAV: Array<{ id: string; label: string; icon: ReactNode }> = [
  { id: "market", label: "市场", icon: <Icon d="M4 19V9l8-6 8 6v10H4zm4-2h4v-5H8v5z" /> },
  { id: "limit", label: "涨停", icon: <Icon d="M5 19h14v-2H5v2zm2-4h10l-1.5-9h-7L7 15zm5-11 2 2H10l2-2z" /> },
  { id: "sector", label: "板块", icon: <Icon d="M4 4h7v7H4V4zm9 0h7v7h-7V4zM4 13h7v7H4v-7zm9 3h7v4h-7v-4z" /> },
  { id: "lhb", label: "龙虎", icon: <Icon d="M5 18 8 8h2l1.2 4L13 8h2l3 10h-2.2l-.6-2H8.8l-.6 2H5zm4.4-4h5.2L13 10h-2l-1.6 4z" /> },
  { id: "auction", label: "竞价", icon: <Icon d="M5 20V8h3v12H5zm5.5 0V4h3v16h-3zM16 20v-8h3v8h-3z" /> },
  { id: "stock", label: "个股", icon: <Icon d="M7 20V10h3v10H7zm7-16h3v16h-3V4zM4 14h3v6H4v-6z" /> },
  { id: "feng", label: "风口", icon: <Icon d="M4 13c4-8 12-8 16 0-4 8-12 8-16 0zm8-3a3 3 0 100 6 3 3 0 000-6z" /> },
  { id: "theme", label: "题材", icon: <Icon d="M6 4h12v3H6V4zm0 5h12v11H6V9zm3 3v5h6v-5H9z" /> },
  { id: "live", label: "直播", icon: <Icon d="M4 7h10v10H4V7zm12 2 4-2v10l-4-2V9z" /> },
  { id: "news", label: "资讯", icon: <Icon d="M5 4h14v16H5V4zm3 3v2h8V7H8zm0 4v2h8v-2H8zm0 4v2h5v-2H8z" /> },
];

const TITLES: Record<string, { title: string; sub: string }> = {
  market: { title: "市场概览", sub: "情绪 · 量能 · 指数 · 涨停梯队" },
  limit: { title: "涨停分析", sub: "天梯、分板、破板、原因与回撤" },
  sector: { title: "板块数据", sub: "强度排名、行业地区与竞价异动" },
  lhb: { title: "龙虎榜", sub: "上榜个股、游资动向与席位" },
  auction: { title: "竞价数据", sub: "早盘竞价与尾盘抢筹" },
  stock: { title: "股票数据", sub: "所属板块、新高与区间统计" },
  feng: { title: "风口概念", sub: "最强风口与概念强度" },
  theme: { title: "题材库", sub: "搜索题材并查看成分股逻辑" },
  live: { title: "大盘直播", sub: "盘中解读与涨跌统计" },
  news: { title: "最新消息", sub: "公告与盘面快讯" },
};

function parseHash() {
  const raw = window.location.hash.replace(/^#\/?/, "");
  return NAV.some((n) => n.id === raw) ? raw : "market";
}

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}

function Shell() {
  const { date, holidays, setDate, settings, saveSettings, refresh, isToday } = useApp();
  const [page, setPage] = useState(parseHash);
  const [clock, setClock] = useState(formatClock);
  const [openSettings, setOpenSettings] = useState(false);

  useEffect(() => {
    const onHash = () => setPage(parseHash());
    window.addEventListener("hashchange", onHash);
    const timer = window.setInterval(() => setClock(formatClock()), 1000);
    return () => {
      window.removeEventListener("hashchange", onHash);
      window.clearInterval(timer);
    };
  }, []);

  const meta = TITLES[page];

  const go = (id: string) => {
    window.location.hash = `/${id}`;
    setPage(id);
  };

  const body = useMemo(() => {
    switch (page) {
      case "limit":
        return <LimitUpPage />;
      case "sector":
        return <SectorsPage />;
      case "lhb":
        return <LhbPage />;
      case "auction":
        return <AuctionPage />;
      case "stock":
        return <StocksPage />;
      case "feng":
        return <FengkouPage />;
      case "theme":
        return <ThemePage />;
      case "live":
        return <LivePage />;
      case "news":
        return <NewsPage />;
      default:
        return <MarketPage />;
    }
  }, [page]);

  return (
    <div className="app">
      <aside className="rail">
        <div className="brand" title="开盘啦">开</div>
        {NAV.map((item) => (
          <button key={item.id} className={`nav-btn ${page === item.id ? "active" : ""}`} onClick={() => go(item.id)}>
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
        <div className="rail-space" />
      </aside>
      <main className="shell">
        <header className="topbar">
          <div>
            <h1>开盘啦 · {meta.title}</h1>
            <div className="sub">{meta.sub}</div>
          </div>
          <div className="grow" />
          <span className="mono faint">{clock} 北京</span>
          {isToday ? <span className="pill gold">今日</span> : <span className="pill">历史 {date}</span>}
          <div className="date-ctrl">
            <button onClick={() => setDate(shiftTradingDay(date, -1, holidays))} aria-label="上一交易日">‹</button>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            <button onClick={() => setDate(shiftTradingDay(date, 1, holidays))} aria-label="下一交易日">›</button>
          </div>
          <button className="ghost-btn" onClick={() => setDate(lastTradingDay(chinaDate(), holidays))}>
            回到今日
          </button>
          <button className="ghost-btn" onClick={refresh}>刷新</button>
          <button className="ghost-btn" onClick={() => setOpenSettings(true)}>设置</button>
        </header>
        <section className="page">{body}</section>
      </main>
      {openSettings && (
        <Modal title="接口设置" onClose={() => setOpenSettings(false)}>
          <form
            className="settings-form"
            onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              saveSettings({
                token: String(fd.get("token") || "").trim(),
                userId: String(fd.get("userId") || "").trim(),
              });
              setOpenSettings(false);
            }}
          >
            <p className="tip">部分竞价 / 风口接口需要 Token 与 UserID。留空也可浏览公开复盘数据。</p>
            <div className="field">
              <label>Token</label>
              <input name="token" defaultValue={settings.token} placeholder="可选" />
            </div>
            <div className="field">
              <label>UserID</label>
              <input name="userId" defaultValue={settings.userId} placeholder="可选" />
            </div>
            <button className="ghost-btn" type="submit">保存</button>
          </form>
        </Modal>
      )}
    </div>
  );
}

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}
