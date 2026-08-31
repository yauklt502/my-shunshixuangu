import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "龙头88 · 板块角色拆解",
  description: "前三热点板块的连板龙头、趋势龙头、中军、跟风、补涨、卡位六类角色实时拆解。",
};

export default function LongTou88Layout({ children }: LayoutProps<"/longtou88">) {
  return children;
}
