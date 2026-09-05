import { useEffect, useMemo, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { api } from '../lib/api'

function StockCharts({
  daily,
  intraday,
  preClose,
}: {
  daily: any[]
  intraday: any[]
  preClose?: number
}) {
  const dailyOpt = useMemo(() => {
    const dates = daily.map((d) => d.date || d.time)
    const values = daily.map((d) => [d.open, d.close, d.low, d.high])
    const vols = daily.map((d) => d.volume || 0)
    return {
      backgroundColor: 'transparent',
      animation: false,
      legend: { data: ['日K', '成交量'], top: 0, textStyle: { color: '#475569' } },
      grid: [
        { left: 48, right: 16, top: 28, height: '58%' },
        { left: 48, right: 16, top: '76%', height: '16%' },
      ],
      xAxis: [
        { type: 'category', data: dates, boundaryGap: true, axisLabel: { color: '#64748b' } },
        { type: 'category', gridIndex: 1, data: dates, axisLabel: { show: false } },
      ],
      yAxis: [
        { scale: true, splitLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' } },
        { scale: true, gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } },
      ],
      dataZoom: [{ type: 'inside', xAxisIndex: [0, 1], start: Math.max(0, 100 - Math.min(60, dates.length)), end: 100 }],
      series: [
        {
          name: '日K',
          type: 'candlestick',
          data: values,
          itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' },
        },
        { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: vols, itemStyle: { color: '#93c5fd' } },
      ],
    }
  }, [daily])

  const intraOpt = useMemo(() => {
    const times = intraday.map((p) => p.time)
    const prices = intraday.map((p) => p.price)
    const avgs = intraday.map((p) => p.avg_price ?? p.price)
    return {
      backgroundColor: 'transparent',
      animation: false,
      legend: { data: ['分时', '均价'], top: 0, textStyle: { color: '#475569' } },
      grid: { left: 48, right: 16, top: 28, bottom: 28 },
      xAxis: { type: 'category', data: times, axisLabel: { color: '#64748b', interval: 29 } },
      yAxis: { scale: true, splitLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' } },
      series: [
        {
          name: '分时',
          type: 'line',
          showSymbol: false,
          data: prices,
          lineStyle: { width: 1.6, color: '#2563eb' },
          markLine: preClose
            ? {
                symbol: 'none',
                label: { formatter: '昨收', color: '#64748b' },
                lineStyle: { type: 'dashed', color: '#94a3b8' },
                data: [{ yAxis: preClose }],
              }
            : undefined,
        },
        { name: '均价', type: 'line', showSymbol: false, data: avgs, lineStyle: { width: 1.2, color: '#f59e0b' } },
      ],
    }
  }, [intraday, preClose])

  return (
    <div className="charts">
      <div className="chart-box">
        <ReactECharts option={dailyOpt as any} style={{ height: 300 }} notMerge />
      </div>
      <div className="chart-box">
        <ReactECharts option={intraOpt as any} style={{ height: 300 }} notMerge />
      </div>
    </div>
  )
}

export function StockPanelModal({
  code,
  name,
  meta,
  onClose,
}: {
  code: string
  name?: string
  meta?: any
  onClose: () => void
}) {
  const [data, setData] = useState<any>(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setErr('')
    api
      .panel(code)
      .then((d) => {
        if (alive) setData(d)
      })
      .catch((e) => {
        if (alive) setErr(String(e.message || e))
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [code])

  const quote = data?.quote
  const depth = data?.depth

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <div>
            <strong>
              {name || quote?.name || code} <span className="muted">{code}</span>
            </strong>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              {meta?.role_label ? `${meta.role_label} · ${meta.position}` : '个股面板'}
              {meta?.reason ? ` · ${meta.reason}` : ''}
              {data?.source ? ` · 源:${data.source}` : ''}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {quote && (
              <div style={{ textAlign: 'right' }}>
                <div className={(quote.change_pct ?? 0) >= 0 ? 'up' : 'down'} style={{ fontSize: 20, fontWeight: 700 }}>
                  {Number(quote.price || 0).toFixed(2)}
                </div>
                <div className={(quote.change_pct ?? 0) >= 0 ? 'up' : 'down'} style={{ fontSize: 12 }}>
                  {Number(quote.change_pct || 0).toFixed(2)}%
                </div>
              </div>
            )}
            <button className="btn" onClick={onClose}>
              关闭
            </button>
          </div>
        </div>
        <div className="modal-bd">
          {loading && <div className="empty">加载 Tick Stock Panel 数据…</div>}
          {err && <div className="empty">{err}</div>}
          {!loading && !err && data && (
            <>
              <StockCharts
                daily={data.daily || data.daily_bars || []}
                intraday={data.intraday || []}
                preClose={quote?.pre_close}
              />
              <div className="depth">
                <div className="side">
                  <strong className="ask">卖五档</strong>
                  {(depth?.asks || []).map((a: any, i: number) => (
                    <div key={`a${i}`} style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                      <span>{Number(a.price || 0).toFixed(2)}</span>
                      <span>{a.volume}</span>
                    </div>
                  ))}
                </div>
                <div className="side">
                  <strong className="bid">买五档</strong>
                  {(depth?.bids || []).map((b: any, i: number) => (
                    <div key={`b${i}`} style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                      <span>{Number(b.price || 0).toFixed(2)}</span>
                      <span>{b.volume}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}