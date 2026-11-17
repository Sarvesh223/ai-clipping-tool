import React from 'react'; import { api, mmss } from '../services/api.js'; import { usePoll } from '../hooks/usePoll.js'; import { Stat, Badge, Empty, Err } from '../components/ui.jsx'
export default function Dashboard() {
  const [ps, err] = usePoll(api.projects, 3000); const [h] = usePoll(api.health, 0); const list = ps || []
  const clips = list.reduce((a, p) => a + (p.clip_count || 0), 0); const best = Math.max(0, ...list.map(p => p.best || 0))
  return (<div className="space-y-6 fade"><div className="flex items-end justify-between"><div><h1 className="text-2xl font-semibold text-white">Dashboard</h1><p className="text-sm text-slate-400">Find the best moments in any video — on your own machine.</p></div><a href="#/new" className="btn-primary">＋ New project</a></div>
    <Err>{err}</Err>
    {h && (!h.hardware.ffmpeg || !h.ollama.ok) && <div className="card border-amber-500/30 p-4 text-sm text-amber-200">{!h.hardware.ffmpeg && <div>FFmpeg not found. Run <code>winget install Gyan.FFmpeg</code> and restart.</div>}{!h.ollama.ok && <div>Ollama: {h.ollama.error}</div>}</div>}
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4"><Stat label="Videos" value={list.length} /><Stat label="Clips generated" value={clips} /><Stat label="Best score" value={best ? Math.round(best) : null} /><Stat label="GPU" value={h?.hardware.gpu ? (h.hardware.cuda ? 'CUDA ✓' : 'Detected') : 'CPU'} hint={h?.hardware.gpu} /></div>
    <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Recent projects</h2>
    {list.length === 0 ? <Empty>No projects yet. Paste a YouTube link to get started.</Empty> :
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{list.slice(0, 6).map(p => <a key={p.id} href={p.status === 'completed' ? `#/results/${p.id}` : `#/analysis/${p.id}`} className="card overflow-hidden transition hover:-translate-y-0.5 hover:border-brand-purple/40">
        <div className="aspect-video bg-ink-700">{p.thumb && <img src={p.thumb} className="h-full w-full object-cover" referrerPolicy="no-referrer" />}</div>
        <div className="space-y-2 p-4"><div className="line-clamp-2 text-sm font-medium text-white">{p.title}</div><div className="flex items-center justify-between text-xs text-slate-400"><span>{mmss(p.duration)} · {p.clip_count} clips</span><Badge status={p.status} /></div></div></a>)}</div>}</div>)
}
