import React from 'react'
export const STAGES = [['downloading', 'Downloading'], ['extracting_audio', 'Extracting audio'], ['transcribing', 'Transcribing'], ['understanding', 'Understanding content'], ['ranking', 'Ranking moments'], ['rendering', 'Rendering videos'], ['completed', 'Completed']]
export const Stat = ({ label, value, hint }) => (<div className="card p-5 fade"><div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
  <div className="mt-1 bg-gradient-to-r from-brand-purple to-brand-electric bg-clip-text text-3xl font-semibold text-transparent">{value ?? '—'}</div>{hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}</div>)
export const Badge = ({ status }) => { const c = { completed: 'bg-emerald-500/15 text-emerald-300', running: 'bg-brand-blue/20 text-sky-300', queued: 'bg-slate-500/20 text-slate-300', failed: 'bg-red-500/15 text-red-300', cancelled: 'bg-amber-500/15 text-amber-300', ready: 'bg-emerald-500/15 text-emerald-300', rendering: 'bg-brand-blue/20 text-sky-300', pending: 'bg-slate-500/20 text-slate-300' }
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${c[status] || c.queued}`}>{status}</span> }
export const Bar = ({ done, total }) => { const known = total > 0; const pct = known ? Math.min(100, (done / total) * 100) : null
  return (<div className="h-2 w-full overflow-hidden rounded-full bg-ink-700">{known ? <div className="h-full rounded-full bg-gradient-to-r from-brand-purple to-brand-electric transition-all duration-500" style={{ width: pct + '%' }} />
    : <div className="h-full w-1/3 animate-pulse rounded-full bg-brand-purple/60" />}</div>) }   // indeterminate when the backend has no real number
export const Score = ({ v }) => { const c = v >= 80 ? 'text-emerald-300 border-emerald-400/40' : v >= 60 ? 'text-sky-300 border-sky-400/40' : 'text-amber-300 border-amber-400/40'
  return <div className={`grid h-12 w-12 place-items-center rounded-full border-2 text-sm font-semibold ${c}`}>{Math.round(v)}</div> }
export const Stepper = ({ stage, status }) => { const idx = STAGES.findIndex(s => s[0] === stage)
  return (<ol className="space-y-2">{STAGES.map(([k, name], i) => { const done = status === 'completed' || i < idx; const cur = i === idx && status === 'running'
    return (<li key={k} className="flex items-center gap-3 text-sm"><span className={`grid h-6 w-6 place-items-center rounded-full text-xs ${done ? 'bg-emerald-500/80 text-white' : cur ? 'bg-brand-purple text-white animate-pulse' : 'bg-ink-700 text-slate-500'}`}>{done ? '✓' : i + 1}</span>
      <span className={done || cur ? 'text-slate-100' : 'text-slate-500'}>{name}</span></li>) })}</ol>) }
export const Empty = ({ children }) => <div className="card grid place-items-center p-12 text-center text-slate-400">{children}</div>
export const Err = ({ children }) => children ? <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{children}</div> : null
