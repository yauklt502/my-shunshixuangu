import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import html2canvas from 'html2canvas'
import { Camera, RefreshCw, X } from 'lucide-react'
import { api } from './lib/api'
import { StockPanelModal } from './components/StockPanel'

type Role = 'all' | 'dragon' | 'mid' | 'catchup' | 'follower'
type View = 'stocks' | 'themes'

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

const ROLE_LABEL: Record<string, string> = {
  all: '全部',
  dragon: '龙头',
  mid: '中位股',
  catchup: '补涨龙',
  follower: '跟风',
}

function themeRoleCount(t: any, role: string) {
  if (role === 'dragon') return t.dragon ? 1 : 0
  if (role === 'mid') return (t.mid || []).length
  if (role === 'catchup') return (t.catchup || []).length
  if (role === 'follower') return (t.all || []).filter((s: any) => s.role === 'follower').length
  return t.count || 0
}

export default function App() {
  const [date, setDate] = useState(todayStr())
  const [providers, setProviders] = useState<any[]>([])
  const [active, setActive] = useState('eastmoney')
  const [ladder, setLadder] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<{ code: string; name?: string; meta?: any } | null>(null)
  const [filter, setFilter] = useState<{ view: View; role: Role; theme: string | null }>({
    view: 'stocks',
    role: 'all',
    theme: null,
  })
  const { view, role: filterRole, theme: filterTheme } = filter
  const captureRef = useRef<HTMLDivElement>(null)
  const resultRef = useRef<HTMLDivElement>(null)

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

  const allStocks = ladder?.stocks || []
  const allThemes = ladder?.themes || []

  const stocks = useMemo(() => {
    let list = allStocks
    if (filterTheme) list = list.filter((s: any) => s.theme === filterTheme)
    if (filterRole !== 'all') list = list.filter((s: any) => s.role === filterRole)
    return list
  }, [allStocks, filterRole, filterTheme])

  const themes = useMemo(() => {
    if (!filterTheme) return allThemes
    return allThemes.filter((t: any) => t.theme === filterTheme)
  }, [allThemes, filterTheme])

  function scrollToResult() {
    requestAnimationFrame(() => {
      resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }

  function showRole(role: Role) {
    setFilter((prev) => {
      const same = prev.view === 'stocks' && prev.role === role && !prev.theme
      if (same && role !== 'all') {
        return { view: 'stocks', role: 'all', theme: null }
      }
      return { view: 'stocks', role, theme: null }
    })
    scrollToResult()
  }

  function showThemes() {
    setFilter((prev) =>
      prev.view === 'themes' ? { view: 'stocks', role: 'all', theme: null } : { view: 'themes', role: 'all', theme: null },
    )
    scrollToResult()
  }

  function showTheme(theme: string) {
    setFilter((prev) => {
      if (prev.view === 'stocks' && prev.theme === theme) {
        return { view: 'stocks', role: 'all', theme: null }
      }
      return { view: 'stocks', role: 'all', theme }
    })
    scrollToResult()
  }

  function clearFilters() {
    setFilter({ view: 'stocks', role: 'all', theme: null })
  }

  function openStock(s: any) {
    setSelected({ code: stockCode(s), name: s.name, meta: s })
  }

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

  const summary = ladder?.summary || {}
  const filterActive = filterRole !== 'all' || !!filterTheme || view === 'themes'
  const resultTitle = view === 'themes'
    ? `题材列表（${allThemes.length}）`
    : filterTheme
      ? `${filterTheme} · ${ROLE_LABEL[filterRole]}（${stocks.length}）`
      : `${ROLE_LABEL[filterRole]}结果（${stocks.length}）`

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
            <article
              key={c.role}
              className={`contrast-card clickable${filterRole === c.role && view === 'stocks' ? ' active' : ''}`}
              role="button"
              tabIndex={0}
              onClick={() => showRole(c.role)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  showRole(c.role)
                }
              }}
            >
              <span className={roleClass(c.role)}>{c.label}</span>
              <h3>{c.label}</h3>
              <p><b>时机：</b>{c.timing}</p>
              <p><b>位置：</b>{c.position}</p>
              <p><b>对龙头：</b>{c.vs_leader}</p>
              <p><b>风险：</b>{c.risk}</p>
              <p className="card-hint">点击查看{c.label}分类结果</p>
            </article>
          ))}
        </section>

        <section className="summary-row" aria-label="分类统计">
          <div className="pill">日期 <b>{ladder?.trade_date || date}</b></div>
          <div className="pill">数据源 <b>{ladder?.provider || active}</b></div>
          <button
            type="button"
            className={`pill clickable${view === 'themes' ? ' active' : ''}`}
            onClick={showThemes}
          >
            题材 <b>{summary.themes ?? '-'}</b>
          </button>
          <button
            type="button"
            className={`pill clickable${view === 'stocks' && filterRole === 'dragon' && !filterTheme ? ' active' : ''}`}
            onClick={() => showRole('dragon')}
          >
            龙头 <b>{summary.dragon ?? '-'}</b>
          </button>
          <button
            type="button"
            className={`pill clickable${view === 'stocks' && filterRole === 'mid' && !filterTheme ? ' active' : ''}`}
            onClick={() => showRole('mid')}
          >
            中位股 <b>{summary.mid ?? '-'}</b>
          </button>
          <button
            type="button"
            className={`pill clickable${view === 'stocks' && filterRole === 'catchup' && !filterTheme ? ' active' : ''}`}
            onClick={() => showRole('catchup')}
          >
            补涨龙 <b>{summary.catchup ?? '-'}</b>
          </button>
          <button
            type="button"
            className={`pill clickable${view === 'stocks' && filterRole === 'follower' && !filterTheme ? ' active' : ''}`}
            onClick={() => showRole('follower')}
          >
            跟风 <b>{summary.follower ?? '-'}</b>
          </button>
          <button
            type="button"
            className={`pill clickable${view === 'stocks' && filterRole === 'all' && !filterTheme ? ' active' : ''}`}
            onClick={() => showRole('all')}
          >
            涨停池 <b>{summary.total ?? '-'}</b>
          </button>
        </section>

        {filterActive && (
          <div className="filter-bar">
            <span>
              当前查看：<b>{view === 'themes' ? '全部题材' : resultTitle}</b>
            </span>
            <button type="button" className="btn ghost" onClick={clearFilters}>
              <X size={14} /> 清除筛选
            </button>
          </div>
        )}

        {error && (
          <div className="panel">
            <div className="empty">{error}</div>
          </div>
        )}

        <section className="grid-2" ref={resultRef}>
          <div className="panel">
            <div className="panel-hd">
              <h2>{view === 'themes' ? '题材分类（点击进入该题材）' : '分类结果（点击个股查看日K/分时/五档）'}</h2>
              <span className="muted">{view === 'themes' ? `${allThemes.length} 个题材` : `${stocks.length} 只`}</span>
            </div>
            <div className="panel-bd" style={{ maxHeight: 640, overflow: 'auto', padding: 0 }}>
              {view === 'themes' ? (
                <table>
                  <thead>
                    <tr>
                      <th>题材</th>
                      <th>高度</th>
                      <th>只数</th>
                      <th>龙头</th>
                      <th>中位</th>
                      <th>补涨</th>
                      <th>跟风</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allThemes.map((t: any) => (
                      <tr key={t.theme} onClick={() => showTheme(t.theme)}>
                        <td><b>{t.theme}</b></td>
                        <td className="up">{t.max_boards} 板</td>
                        <td>{t.count}</td>
                        <td>{themeRoleCount(t, 'dragon')}</td>
                        <td>{themeRoleCount(t, 'mid')}</td>
                        <td>{themeRoleCount(t, 'catchup')}</td>
                        <td>{themeRoleCount(t, 'follower')}</td>
                      </tr>
                    ))}
                    {!allThemes.length && (
                      <tr>
                        <td colSpan={7}><div className="empty">{loading ? '加载中…' : '暂无题材'}</div></td>
                      </tr>
                    )}
                  </tbody>
                </table>
              ) : (
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
                      <tr key={`${stockCode(s)}-${s.role}`} onClick={() => openStock(s)}>
                        <td><span className={roleClass(s.role)}>{s.role_label}</span></td>
                        <td>{s.code}</td>
                        <td>{s.name}</td>
                        <td>
                          <button
                            type="button"
                            className="linkish"
                            onClick={(e) => {
                              e.stopPropagation()
                              showTheme(s.theme)
                            }}
                          >
                            {s.theme}
                          </button>
                        </td>
                        <td className="up">{s.boards}</td>
                        <td>{s.position}</td>
                        <td>{s.first_time}</td>
                        <td className="muted" style={{ maxWidth: 220, whiteSpace: 'normal' }}>{s.reason}</td>
                      </tr>
                    ))}
                    {!stocks.length && (
                      <tr>
                        <td colSpan={8}>
                          <div className="empty">
                            {loading
                              ? '加载中…'
                              : filterRole === 'mid'
                                ? '今日暂无中位股（需题材内存在 3~5 板且非龙头的标的）'
                                : filterRole === 'catchup'
                                  ? '今日暂无补涨龙（需龙头已到高位且出现低位启动）'
                                  : filterTheme
                                    ? `「${filterTheme}」下暂无${ROLE_LABEL[filterRole]}`
                                    : '暂无数据（可切换历史日期复盘）'}
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panel-hd">
              <h2>题材梯队（点击题材查看全部个股）</h2>
              <span className="muted">{filterTheme ? filterTheme : '龙头 → 中位 → 补涨 → 跟风'}</span>
            </div>
            <div className="panel-bd theme-list">
              {themes.map((t: any) => {
                const members = t.all || []
                return (
                  <div
                    className={`theme-card clickable${filterTheme === t.theme ? ' active' : ''}`}
                    key={t.theme}
                    role="button"
                    tabIndex={0}
                    onClick={() => showTheme(t.theme)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        showTheme(t.theme)
                      }
                    }}
                  >
                    <header>
                      <strong>{t.theme}</strong>
                      <span className="muted">高度 {t.max_boards} 板 · {t.count} 只</span>
                    </header>
                    <div className="theme-meta">
                      龙头 {themeRoleCount(t, 'dragon')} · 中位 {themeRoleCount(t, 'mid')} · 补涨 {themeRoleCount(t, 'catchup')} · 跟风 {themeRoleCount(t, 'follower')}
                    </div>
                    <div className="stocks">
                      {members.map((s: any) => (
                        <button
                          key={`${stockCode(s)}-${s.role}`}
                          type="button"
                          className="stock-chip"
                          onClick={(e) => {
                            e.stopPropagation()
                            openStock(s)
                          }}
                        >
                          <span className={roleClass(s.role)}>{s.role_label}</span> {s.name} {s.boards}板
                        </button>
                      ))}
                      {!members.length && <span className="muted">该题材暂无个股</span>}
                    </div>
                  </div>
                )
              })}
              {!themes.length && <div className="empty">暂无题材梯队</div>}
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
