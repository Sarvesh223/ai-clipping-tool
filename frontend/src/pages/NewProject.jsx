import React, { useState } from 'react'; import { api } from '../services/api.js'; import { Err } from '../components/ui.jsx'
export const AUDIENCES = ['General audience', 'Entrepreneurs', 'Finance', 'Technology', 'Fitness', 'Education', 'Entertainment']
export const STYLES = ['Educational', 'Emotional', 'Controversial', 'Motivational', 'Storytelling', 'Funny']
export default function NewProject() {
  const [url, setUrl] = useState(''); const [q, setQ] = useState(720); const [aud, setAud] = useState(AUDIENCES[0]); const [sty, setSty] = useState(STYLES[0]); const [file, setFile] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  const go = async () => { setBusy(true); setErr(''); try { const p = file ? await api.upload(file, aud, sty) : await api.create({ url, quality: +q, audience: aud, style: sty }); location.hash = `#/analysis/${p.id}` } catch (e) { setErr(e.message) } setBusy(false) }
  const Sel = ({ l, v, set, o }) => <div><label className="label">{l}</label><select className="input" value={v} onChange={e => set(e.target.value)}>{o.map(x => <option key={x} value={Array.isArray(x) ? x[0] : x}>{Array.isArray(x) ? x[1] : x}</option>)}</select></div>
  return (<div className="mx-auto max-w-2xl space-y-6 fade"><h1 className="text-2xl font-semibold text-white">New project</h1>
    <div className="card space-y-5 p-6"><div><label className="label">YouTube URL</label><input className="input" placeholder="https://www.youtube.com/watch?v=…" value={url} onChange={e => { setUrl(e.target.value); setFile(null) }} /></div>
      <div className="flex items-center gap-3 text-xs text-slate-500"><div className="h-px flex-1 bg-white/5" />or import a file<div className="h-px flex-1 bg-white/5" /></div>
      <input type="file" accept=".mp4,.mov,.mkv,.webm" onChange={e => { setFile(e.target.files[0]); setUrl('') }} className="block w-full text-sm text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-ink-700 file:px-3 file:py-2 file:text-slate-200" />
      <div className="grid gap-4 sm:grid-cols-3"><Sel l="Quality" v={q} set={setQ} o={[[480, '480p'], [720, '720p'], [1080, '1080p']]} /><Sel l="Audience" v={aud} set={setAud} o={AUDIENCES} /><Sel l="Style" v={sty} set={setSty} o={STYLES} /></div>
      <Err>{err}</Err><button className="btn-primary w-full" disabled={busy || (!url && !file)} onClick={go}>{busy ? 'Reading video…' : 'Analyse & generate clips'}</button>
      <p className="text-xs text-slate-500">Only download content you have the right to use. DRM and access restrictions are never bypassed.</p></div></div>)
}
