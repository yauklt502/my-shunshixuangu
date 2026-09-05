import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import html2canvas from 'html2canvas'
import { Camera, RefreshCw } from 'lucide-react'
import { api } from './lib/api'
import { StockPanelModal } from './components/StockPanel'

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${`${d.getMonth() + 1}`.padStart(2, '0')}-${`${d.getDate()}`.padStart(2, '0')}`
}

function roleClass(role: string) {
  if (role === 'dragon') return 'role-chip'
  if (role === 'mid') return 'role-chip mid'
  if (role === 'catchup') return 'role-chip catchup'
  return 'role-chip follower'
}

function stockCode(s: any) {
  return s.symbol || `${s.market || ''}${s.code}`
}

export default function App() {
  const [date, setDate] = useState(todayStr())
  const [providers, setProviders] = useState<any[]>([])
  const [active, setActive] = useState('eastmoney')
  const [ladder, setLadder] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<{ code: string; name?: string; meta?: any } | null>(null)
  const [filterRole, setFilterRole] = useState('all')
  const captureRef = useRef<HTMLDivElement>(null)

  const loadProviders = useCallback(async () => {
    const d = await api.providers()
    setProviders(d.items || [])
    setActive(d.active)
  }, [])

  const loadLadder = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setLadder(await api.ladder(date))
    } catch (e: any) {
      setError(String(e.message || e))
    } finally {
      setLoading(false)
    }
  }, [date])

  useEffect(() => {
    loadProviders().catch((e) => setError(String(e.message || e)))
  }, [loadProviders])

  useEffect(() => {
    loadLadder()
  }, [loadLadder])

  const stocks = useMemo(() => {
    const list = ladder?.stocks || []
    if (filterRole === 'all') return list
    return list.filter((s: any) => s.role === filterRole)
  }, [ladder, filterRole])

  async function switchProvider(name: string) {
    await api.activate(name)
    setActive(name)
    await loadProviders()
    await loadLadder()
  }

  async function screenshot() {
    if (!captureRef.current) return
    const canvas = await html2canvas(captureRef.current, { backgroundColor: '#f4f7fb', scale: 2, useCORS: true })
    const a = document.createElement('a')
    a.href = canvas.toDataURL('image/png')
    a.download = `role-ladder-${date}.png`
    a.click()
  }

  const contrast = ladder?.contrast || [
    { role: 'dragon', label: '龙头', timing: '主线初期~高潮', position: '题材最高板', vs_leader: '本身即定价锚', risk: '退潮回撤大' },
    { role: 'mid', label: '中位股', timing: '主线中期', position: '约3~5板中位开挂', vs_leader: '伴随扩散，非龙头', risk: '龙头弱时先掉队' },
    { role: 'catchup', label: '补涨龙', timing: '龙头末期/断板前后', position: '低位重新启动', vs_leader: '承接溢出', risk: '鱼尾接力风险大' },
  ]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <strong>顺势选股</strong>
          <span>龙头 · 中位股 · 补涨龙 实时对照</span>
        </div>
        <div className="controls">
          <div className="control">
            <label>复盘日期</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="control">
            <label>数据源</label>
            <select value={active} onChange={(e) => switchProvider(e.target.value)}>
              {providers.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.display_name} {p.health?.ok ? '✓' : '✗'}
                </option>
              ))}
              {!providers.length && (
                <>
                  <option value="eastmoney">东方财富</option>
                  <option value="tdx">通达信</option>
                  <option value="tonghuashun">同花顺口径</option>
                </>
              )}
            </select>
          </div>
          <div className="control">
            <label>角色</label>
            <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)}>
              <option value="all">全部</option>
              <option value="dragon">龙头</option>
              <option value="mid">中位股</option>
              <option value="catchup">补涨龙</option>
              <option value="follower">跟风</option>
            </select>
          </div>
          <button className="btn" onClick={loadLadder} disabled={loading}>
            <RefreshCw size={16} /> {loading ? '刷新中' : '刷新'}
          </button>
          <button className="btn primary" onClick={screenshot}>
            <Camera size={16} /> 一键截图
          </button>
        </div>
      </header>

      <main className="main" ref={captureRef}>
        <section className="hero-contrast">
          {contrast.map((c: any) => (
            <article key={c.role} className="contrast-card">
              <span className={roleClass(c.role)}>{c.label}</span>
              <h3>{c.label}</h3>
              <p><b>时机：</b>{c.timing}</p>
              <p><b>位置：</b>{c.position}</p>
              <p><b>对龙头：</b>{c.vs_leader}</p>
              <p><b>风险：</b>{c.risk}</p>
            </article>
          ))}
        </section>

        <section className="summary-row">
          <div className="pill">日期 <b>{ladder?.trade_date || date}</b></div>
          <div className="pill">数据源 <b>{ladder?.provider || active}</b></div>
          <div className="pill">题材 <b>{ladder?.summary?.themes ?? '-'}</b></div>
          <div className="pill">龙头 <b>{ladder?.summary?.dragon ?? '-'}</b></div>
          <div className="pill">中位股 <b>{ladder?.summary?.mid ?? '-'}</b></div>
          <div className="pill">补涨龙 <b>{ladder?.summary?.catchup ?? '-'}</b></div>
          <div className="pill">涨停池 <b>{ladder?.summary?.total ?? '-'}</b></div>
        </section>

        {error && (
          <div className="panel">
            <div className="empty">{error}</div>
          </div>
        )}

        <section className="grid-2">
          <div className="panel">
            <div className="panel-hd">
              <h2>角色全表（点击查看日K/分时/五档）</h2>
              <span className="muted">{stocks.length} 只</span>
            </div>
            <div className="panel-bd" style={{ maxHeight: 640, overflow: 'auto', padding: 0 }}>
              <table>
                <thead>
                  <tr>
                    <th>角色</th>
                    <th>代码</th>
                    <th>名称</th>
                    <th>题材</th>
                    <th>连板</th>
                    <th>位置</th>
                    <th>封板</th>
                    <th>原因</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((s: any) => (
                    <tr key={`${stockCode(s)}-${s.role}`} onClick={() => setSelected({ code: stockCode(s), name: s.name, meta: s })}>
                      <td><span className={roleClass(s.role)}>{s.role_label}</span></td>
                      <td>{s.code}</td>
                      <td>{s.name}</td>
                      <td>{s.theme}</td>
                      <td className="up">{s.boards}</td>
                      <td>{s.position}</td>
                      <td>{s.first_time}</td>
                      <td className="muted" style={{ maxWidth: 220, whiteSpace: 'normal' }}>{s.reason}</td>
                    </tr>
                  ))}
                  {!stocks.length && (
                    <tr>
                      <td colSpan={8}><div className="empty">{loading ? '加载中…' : '暂无数据（可切换历史日期复盘）'}</div></td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel">
            <div className="panel-hd">
              <h2>题材梯队关系</h2>
              <span className="muted">龙头 → 中位 → 补涨</span>
            </div>
            <div className="panel-bd theme-list">
              {(ladder?.themes || []).slice(0, 20).map((t: any) => (
                <div className="theme-card" key={t.theme}>
                  <header>
                    <strong>{t.theme}</strong>
                    <span className="muted">高度 {t.max_boards} 板 · {t.count} 只</span>
                  </header>
                  <div className="stocks">
                    {t.dragon && (
                      <button className="stock-chip" onClick={() => setSelected({ code: stockCode(t.dragon), name: t.dragon.name, meta: t.dragon })}>
                        <span className="role-chip">龙头</span> {t.dragon.name} {t.dragon.boards}板
                      </button>
                    )}
                    {(t.mid || []).map((s: any) => (
                      <button key={s.code + 'm'} className="stock-chip" onClick={() => setSelected({ code: stockCode(s), name: s.name, meta: s })}>
                        <span className="role-chip mid">中位</span> {s.name} {s.boards}板
                      </button>
                    ))}
                    {(t.catchup || []).map((s: any) => (
                      <button key={s.code + 'c'} className="stock-chip" onClick={() => setSelected({ code: stockCode(s), name: s.name, meta: s })}>
                        <span className="role-chip catchup">补涨</span> {s.name} {s.boards}板
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              {!ladder?.themes?.length && <div className="empty">暂无题材梯队</div>}
            </div>
          </div>
        </section>
      </main>

      {selected && (
        <StockPanelModal code={selected.code} name={selected.name} meta={selected.meta} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}