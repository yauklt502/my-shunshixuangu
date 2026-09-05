import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import html2canvas from 'html2canvas'
import { Camera, RefreshCw, X } from 'lucide-react'
import { api } from './lib/api'
import { StockPanelModal } from './components/StockPanel'

type Role =
  | 'all'
  | 'dragon'
  | 'chief'
  | 'sentiment'
  | 'dragon2'
  | 'dragon3'
  | 'theme_dragon'
  | 'mid'
  | 'catchup'
  | 'follower'
type View = 'stocks' | 'themes'

const DRAGON_FAMILY = new Set(['chief', 'sentiment', 'dragon2', 'dragon3', 'theme_dragon', 'dragon'])

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${`${d.getMonth() + 1}`.padStart(2, '0')}-${`${d.getDate()}`.padStart(2, '0')}`
}

function roleClass(role: string) {
  if (role === 'chief') return 'role-chip chief'
  if (role === 'sentiment') return 'role-chip sentiment'
  if (role === 'dragon2' || role === 'dragon' || role === 'theme_dragon') return 'role-chip'
  if (role === 'dragon3') return 'role-chip dragon3'
  if (role === 'mid') return 'role-chip mid'
  if (role === 'catchup') return 'role-chip catchup'
  return 'role-chip follower'
}

function stockCode(s: any) {
  return s.symbol || `${s.market || ''}${s.code}`
}

function titleKeys(s: any): string[] {
  return s?.title_keys || (s?.role ? [s.role] : [])
}

function matchRole(s: any, role: Role) {
  if (role === 'all') return true
  const keys = titleKeys(s)
  if (role === 'dragon') return keys.some((k) => DRAGON_FAMILY.has(k))
  return keys.includes(role) || s.role === role
}

const ROLE_LABEL: Record<string, string> = {
  all: '全部',
  dragon: '龙头家族',
  chief: '日内总龙头',
  sentiment: '情绪龙头',
  dragon2: '龙二',
  dragon3: '龙三',
  theme_dragon: '题材龙',
  mid: '中位股',
  catchup: '补涨龙',
  follower: '跟风',
}

const SEATS: { key: Role; label: string; hint: string }[] = [
  { key: 'chief', label: '日内总龙头', hint: '全市场最高连板' },
  { key: 'sentiment', label: '情绪龙头', hint: '主线方向锚' },
  { key: 'dragon2', label: '龙二', hint: '主线第二辨识' },
  { key: 'dragon3', label: '龙三', hint: '主线第三梯队' },
]

function themeRoleCount(t: any, role: string) {
  const members = t.all || []
  if (role === 'dragon') return members.filter((s: any) => matchRole(s, 'dragon')).length
  if (role === 'mid') return (t.mid || []).length
  if (role === 'catchup') return (t.catchup || []).length
  if (role === 'follower') return members.filter((s: any) => s.role === 'follower').length
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
  const dragonLadder = ladder?.dragon_ladder || {}

  const stocks = useMemo(() => {
    let list = allStocks
    if (filterTheme) list = list.filter((s: any) => s.theme === filterTheme)
    if (filterRole !== 'all') list = list.filter((s: any) => matchRole(s, filterRole))
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
    if (!s) return
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

  const contrast = ladder?.contrast || []
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
          <span>总龙头 · 情绪龙 · 龙二龙三 · 中位 / 补涨</span>
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
        <section className="dragon-seats" aria-label="今日龙梯队">
          {SEATS.map((seat) => {
            const s = dragonLadder[seat.key]
            const dual = seat.key === 'chief' && summary.same_chief_sentiment
            const activeSeat = filterRole === seat.key && view === 'stocks' && !filterTheme
            return (
              <article
                key={seat.key}
                className={`seat ${seat.key}${activeSeat ? ' active' : ''}${s ? '' : ' empty'}`}
                role="button"
                tabIndex={0}
                onClick={() => showRole(seat.key)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    showRole(seat.key)
                  }
                }}
              >
                <div className="seat-kicker">
                  <span className={roleClass(seat.key)}>{seat.label}</span>
                  {dual && <span className="role-chip sentiment">兼任情绪龙</span>}
                </div>
                {s ? (
                  <>
                    <button
                      type="button"
                      className="seat-name"
                      onClick={(e) => {
                        e.stopPropagation()
                        openStock(s)
                      }}
                    >
                      {s.name}
                    </button>
                    <div className="seat-meta">
                      <b className="up">{s.boards}板</b>
                      <span>{s.theme || s.industry}</span>
                      <span>{s.first_time || '--'}</span>
                    </div>
                    <p className="seat-reason">{s.reason || seat.hint}</p>
                  </>
                ) : (
                  <>
                    <div className="seat-name muted">今日未形成</div>
                    <p className="seat-reason">{seat.hint} · 主线票不足</p>
                  </>
                )}
              </article>
            )
          })}
        </section>

        {dragonLadder.note && (
          <div className="ladder-note">
            <b>怎么分的：</b>
            {dragonLadder.note}
            {dragonLadder.isolated_height
              ? `（最高板孤立 ≠ 情绪龙；情绪看 ${dragonLadder.emotion_height} 板主线「${dragonLadder.main_theme}」）`
              : `（高度连续时，总龙头往往就是情绪龙头）`}
          </div>
        )}

        <section className="hero-contrast">
          {contrast
            .filter((c: any) => c.role === 'mid' || c.role === 'catchup')
            .map((c: any) => (
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
                <p><b>作用：</b>{c.vs_leader}</p>
                <p><b>风险：</b>{c.risk}</p>
                <p className="card-hint">点击查看{c.label}</p>
              </article>
            ))}
        </section>

        <section className="summary-row" aria-label="分类统计">
          <div className="pill">日期 <b>{ladder?.trade_date || date}</b></div>
          <div className="pill">数据源 <b>{ladder?.provider || active}</b></div>
          <button type="button" className={`pill clickable${view === 'themes' ? ' active' : ''}`} onClick={showThemes}>
            题材 <b>{summary.themes ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'chief' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('chief')}>
            总龙头 <b>{summary.chief ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'sentiment' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('sentiment')}>
            情绪龙 <b>{summary.sentiment ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'dragon2' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('dragon2')}>
            龙二 <b>{summary.dragon2 ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'dragon3' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('dragon3')}>
            龙三 <b>{summary.dragon3 ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'theme_dragon' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('theme_dragon')}>
            题材龙 <b>{summary.theme_dragon ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'mid' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('mid')}>
            中位股 <b>{summary.mid ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'catchup' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('catchup')}>
            补涨龙 <b>{summary.catchup ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'follower' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('follower')}>
            跟风 <b>{summary.follower ?? '-'}</b>
          </button>
          <button type="button" className={`pill clickable${view === 'stocks' && filterRole === 'all' && !filterTheme ? ' active' : ''}`} onClick={() => showRole('all')}>
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
                        <td>
                          <b>{t.theme}</b>
                          {t.is_main && <span className="role-chip sentiment" style={{ marginLeft: 6 }}>主线</span>}
                        </td>
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
                      <th>席位</th>
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
                        <td>
                          <span className="chip-row">
                            {(s.title_keys || [s.role]).map((k: string) => (
                              <span key={k} className={roleClass(k)}>{ROLE_LABEL[k] || s.role_label}</span>
                            ))}
                          </span>
                        </td>
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
                          {s.is_main_theme && <span className="muted"> ·主线</span>}
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
                                  : filterRole === 'dragon3'
                                    ? '今日主线未形成龙三（情绪主线里可排的票不足 3 只）'
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
              <span className="muted">{filterTheme ? filterTheme : dragonLadder.main_theme ? `主线 ${dragonLadder.main_theme}` : '总龙 → 情绪龙 → 龙二龙三'}</span>
            </div>
            <div className="panel-bd theme-list">
              {themes.map((t: any) => {
                const members = t.all || []
                return (
                  <div
                    className={`theme-card clickable${filterTheme === t.theme ? ' active' : ''}${t.is_main ? ' main' : ''}`}
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
                      <strong>
                        {t.theme}
                        {t.is_main && <span className="role-chip sentiment" style={{ marginLeft: 6 }}>情绪主线</span>}
                      </strong>
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
