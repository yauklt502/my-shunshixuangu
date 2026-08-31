import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "趋势龙头 · 五维筛选",
  description: "按方向明确、均线支撑、量价配合、回调浅、板块有配合筛选趋势龙头。",
};

export default function QushiLongTouLayout({ children }: LayoutProps<"/qushi-longtou">) {
  return children;
}
