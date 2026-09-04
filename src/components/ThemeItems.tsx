import type { ThemeItem } from "@/api/services";
import { Empty } from "@/components/ui";
import { openTheme } from "@/lib/nav";

export function ThemeItemList({
  items,
  activeId,
  onSelect,
}: {
  items: ThemeItem[];
  activeId?: string;
  onSelect?: (id: string) => void;
}) {
  if (!items.length) return <Empty text="暂无题材项" />;
  return (
    <div className="theme-items">
      {items.map((item) => (
        <button
          key={item.ID}
          type="button"
          className={`theme-item ${activeId === item.ID ? "active" : ""}`}
          onClick={() => {
            onSelect?.(item.ID);
            openTheme(item.ID);
          }}
        >
          <div className="theme-item-top">
            <b>{item.Name}</b>
            <span className="theme-item-tags">
              {Number(item.Hot) === 1 && <span className="pill gold">热门</span>}
              {Number(item.New) === 1 && <span className="pill">新</span>}
              <span className="pill up">{item.ZTNum ?? 0} 涨停</span>
              {Number(item.UpNum) > 0 && <span className="pill">{item.UpNum} 上涨</span>}
            </span>
          </div>
          {!!item.List?.length && (
            <div className="theme-item-subs">
              {item.List.map((sub) => (
                <span className="pill" key={sub.CID || sub.Name}>
                  {sub.Name}
                </span>
              ))}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
