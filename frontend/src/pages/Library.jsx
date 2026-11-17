import React from 'react'; import { api, mmss } from '../services/api.js'; import { usePoll } from '../hooks/usePoll.js'; import { Badge, Empty, Bar } from '../components/ui.jsx'
export default function Library() {
  const [ps, , reload] = usePoll(api.projects, 3000); const act = async (f) => { await f(); reload() }
  return (<div className="space-y-6 fade"><div className="flex items-center justify-between"><h1 className="text-2xl font-semibold text-white">Video Library</h1><a href="#/new" className="btn-primary">＋ Add</a></div>
    {!ps?.length ? <Empty>Your videos will appear here.</Empty> : <div className="space-y-3">{ps.map(p => <div key={p.id} className="card flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
      <div className="aspect-video w-full shrink-0 overflow-hidden rounded-xl bg-ink-700 sm:w-44">{p.thumb && <img src={p.thumb} className="h-full w-full object-cover" referrerPolicy="no-referrer" />}</div>
      <div className="min-w-0 flex-1 space-y-2"><div className="truncate font-medium text-white">{p.title}</div><div className="flex gap-3 text-xs text-slate-400"><span>{mmss(p.duration)}</span><span>{p.clip_count} clips</span><Badge status={p.status} /></div>{p.status === 'running' && <Bar done={p.done} total={p.total} />}{p.error && <div className="truncate text-xs text-red-300">{p.error}</div>}</div>
      <div className="flex flex-wrap gap-2"><a className="btn-ghost" href={p.status === 'completed' ? `#/results/${p.id}` : `#/analysis/${p.id}`}>Open</a>
        {p.status === 'running' && <button className="btn-ghost" onClick={() => act(() => api.cancel(p.id))}>Cancel</button>}
        {['failed', 'cancelled'].includes(p.status) && <button className="btn-ghost" onClick={() => act(() => api.retry(p.id))}>Retry</button>}
        <button className="btn-danger" onClick={() => confirm('Delete this video and its clips?') && act(() => api.remove(p.id))}>Delete</button></div></div>)}</div>}</div>)
}
