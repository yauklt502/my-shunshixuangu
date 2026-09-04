/** Types mirrored from tick-stock-panel (TickFlow Stock Panel) for the intraday chart. */

export interface MinuteKlineRow {
  datetime: string;
  /** 分钟开盘价; 部分数据源无真实分钟 open, 为 null */
  open: number | null;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
}

export interface PriceLimitInfo {
  rate: number;
  limit_up: number | null;
  limit_down: number | null;
  source: "rule" | "instrument";
}
