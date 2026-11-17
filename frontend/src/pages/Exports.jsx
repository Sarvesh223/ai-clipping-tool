import React from 'react'; import { api } from '../services/api.js'; import { usePoll } from '../hooks/usePoll.js'; import { Empty } from '../components/ui.jsx'
export default function Exports() {
  const [xs] = usePoll(api.exports, 4000)
  return (<div className="space-y-6 fade"><h1 className="text-2xl font-semibold text-white">Export History</h1>{!xs?.length ? <Empty>Exported clips are saved to the <code>exports</code> folder and listed here.</Empty> :
    <div className="card divide-y divide-white/5">{xs.map(x => <div key={x.id} className="flex items-center justify-between gap-4 p-4 text-sm"><div className="min-w-0"><div className="truncate text-slate-200">{x.path.split(/[\\/]/).pop()}</div><div className="truncate text-xs text-slate-500">{x.path}</div></div><div className="shrink-0 text-xs text-slate-400">{new Date(x.created * 1000).toLocaleString()}</div></div>)}</div>}</div>)
}
