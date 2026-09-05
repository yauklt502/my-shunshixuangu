const BASE = ''

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json()
}

export const api = {
  health: () => req<any>('/api/health'),
  providers: () => req<{ items: any[]; active: string }>('/api/providers'),
  activate: (name: string) =>
    req<any>(`/api/providers/${name}/activate`, { method: 'POST' }),
  ladder: (date: string) =>
    req<any>(`/api/ladder?date=${encodeURIComponent(date || '')}`),
  panel: (code: string) => req<any>(`/api/stock/panel/${encodeURIComponent(code)}`),
}