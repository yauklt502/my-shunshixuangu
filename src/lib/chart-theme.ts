/**
 * Chart theme palette — ported from tick-stock-panel `lib/theme.ts`.
 * This app is light-only; keep the light chart tokens.
 */
export interface ChartTheme {
  text: string;
  textStrong: string;
  grid: string;
  border: string;
  crosshair: string;
  crosshairLabelBg: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipText: string;
  infoBarBg: string;
  zoomFill: string;
  fillSubtle: string;
}

export const LIGHT_CHART_THEME: ChartTheme = {
  text: "#71717A",
  textStrong: "#27272A",
  grid: "rgba(0,0,0,0.06)",
  border: "#E4E4E7",
  crosshair: "rgba(0,0,0,0.3)",
  crosshairLabelBg: "#52525B",
  tooltipBg: "rgba(255,255,255,0.97)",
  tooltipBorder: "rgba(0,0,0,0.1)",
  tooltipText: "#27272A",
  infoBarBg: "rgba(244,244,245,0.85)",
  zoomFill: "rgba(0,0,0,0.06)",
  fillSubtle: "rgba(0,0,0,0.04)",
};

export function useChartTheme(): ChartTheme {
  return LIGHT_CHART_THEME;
}
