import React, { useEffect } from 'react'; import { api, mmss } from '../services/api.js'; import { usePoll } from '../hooks/usePoll.js'
import { Stepper, Bar, Badge, Stat, Err } from '../components/ui.jsx'
const UNIT = { downloading: 'bytes', transcribing: 'seconds of audio', understanding: 'chunks', rendering: 'clips' }
export default function Analysis({ id }) {
  const [p, err, reload] = usePoll(() => api.project(id), 1500, [id])
  useEffect(() => { if (p?.status === 'completed') location.hash = `#/results/${id}` }, [p?.status])
  if (!p) return <div className="text-slate-400">{err || 'Loading…'}</div>
  const known = p.total > 0
  return (<div className="space-y-6 fade"><div className="flex items-start justify-between gap-4"><div><h1 className="text-2xl font-semibold text-white">AI Analysis</h1><p className="mt-1 text-sm text-slate-400">{p.title}</p></div><Badge status={p.status} /></div>
    <div className="grid gap-6 md:grid-cols-5"><div className="card p-6 md:col-span-2"><Stepper stage={p.stage} status={p.status} /></div>
      <div className="card space-y-5 p-6 md:col-span-3"><div className="text-sm text-slate-300">Current stage: <b className="text-white">{p.stage || 'waiting in queue'}</b></div>
        <Bar done={p.done} total={p.total} />
        <div className="text-xs text-slate-500">{known ? `${p.done?.toLocaleString()} / ${p.total?.toLocaleString()} ${UNIT[p.stage] || ''}` : 'This stage does not report exact progress, so no percentage is shown.'}</div>
        <div className="grid grid-cols-2 gap-3"><Stat label="Duration" value={mmss(p.duration)} /><Stat label="Elapsed" value={p.stats.processing_s ? `${Math.round(p.stats.processing_s)}s` : '—'} /></div>
        <Err>{p.error}</Err>
        <div className="flex gap-2">{p.status === 'running' && <button className="btn-ghost" onClick={async () => { await api.cancel(id); reload() }}>Cancel</button>}
          {['failed', 'cancelled'].includes(p.status) && <button className="btn-primary" onClick={async () => { await api.retry(id); reload() }}>Retry (resumes from cache)</button>}</div></div></div></div>)
}
