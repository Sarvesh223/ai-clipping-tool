const j = async (r) => { if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || r.statusText) } return r.json() }
const send = (m, u, b) => fetch('/api' + u, { method: m, headers: { 'Content-Type': 'application/json' }, body: b ? JSON.stringify(b) : undefined }).then(j)
export const api = {
  health: () => send('GET', '/health'), projects: () => send('GET', '/projects'), project: (id) => send('GET', `/projects/${id}`),
  create: (b) => send('POST', '/projects', b), cancel: (id) => send('POST', `/projects/${id}/cancel`), retry: (id) => send('POST', `/projects/${id}/retry`),
  remove: (id) => send('DELETE', `/projects/${id}`), settings: () => send('GET', '/settings'), saveSettings: (b) => send('PUT', '/settings', b),
  patchClip: (id, b) => send('PATCH', `/clips/${id}`, b), render: (id) => send('POST', `/clips/${id}/render`), delClip: (id) => send('DELETE', `/clips/${id}`),
  exportClip: (id) => send('POST', `/clips/${id}/export`), exports: () => send('GET', '/exports'),
  upload: (file, audience, style) => { const f = new FormData(); f.append('file', file); f.append('audience', audience); f.append('style', style); return fetch('/api/projects/upload', { method: 'POST', body: f }).then(j) },
  videoUrl: (id, v) => `/api/clips/${id}/video?v=${v || 0}`, thumbUrl: (id, i) => `/api/clips/${id}/thumb/${i}`,
}
export const mmss = (s) => { s = Math.max(0, s || 0); return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}` }
