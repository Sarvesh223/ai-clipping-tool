import React, { useEffect, useState } from 'react'
import Dashboard from '../pages/Dashboard.jsx'; import NewProject from '../pages/NewProject.jsx'; import Library from '../pages/Library.jsx'
import Analysis from '../pages/Analysis.jsx'; import Results from '../pages/Results.jsx'; import Editor from '../pages/Editor.jsx'
import Settings from '../pages/Settings.jsx'; import Exports from '../pages/Exports.jsx'
const NAV = [['', 'Dashboard', '◧'], ['new', 'New Project', '＋'], ['library', 'Video Library', '▤'], ['settings', 'Model Settings', '⚙'], ['exports', 'Export History', '⇩']]
const useHash = () => { const [h, setH] = useState(location.hash.slice(2)); useEffect(() => { const f = () => setH(location.hash.slice(2)); addEventListener('hashchange', f); return () => removeEventListener('hashchange', f) }, []); return h }
export default function App() {
  const h = useHash(); const [page, a, b] = h.split('/'); let view
  if (page === 'new') view = <NewProject /> ; else if (page === 'library') view = <Library />
  else if (page === 'analysis') view = <Analysis id={a} />; else if (page === 'results') view = <Results id={a} />
  else if (page === 'editor') view = <Editor id={a} project={b} />; else if (page === 'settings') view = <Settings />
  else if (page === 'exports') view = <Exports />; else view = <Dashboard />
  return (<div className="flex min-h-screen bg-gradient-to-br from-ink-950 via-ink-900 to-ink-950">
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-white/5 bg-ink-900/80 p-4 md:flex">
      <div className="mb-8 flex items-center gap-2 px-2"><div className="h-8 w-8 rounded-xl bg-gradient-to-br from-brand-purple to-brand-electric" /><div><div className="text-sm font-semibold text-white">Clip Studio</div><div className="text-[10px] uppercase tracking-widest text-slate-500">100% local AI</div></div></div>
      <nav className="space-y-1">{NAV.map(([k, n, i]) => <a key={k} href={'#/' + k} className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition ${page === k || (k === '' && !page) ? 'bg-brand-purple/15 text-white' : 'text-slate-400 hover:bg-ink-800 hover:text-white'}`}><span className="w-4 text-center">{i}</span>{n}</a>)}</nav>
      <div className="mt-auto px-2 text-[11px] leading-relaxed text-slate-500">Nothing leaves your computer. Scores estimate content quality, not virality.</div></aside>
    <main className="min-w-0 flex-1 p-4 md:p-8"><div className="mx-auto max-w-6xl">{view}</div></main></div>)
}
