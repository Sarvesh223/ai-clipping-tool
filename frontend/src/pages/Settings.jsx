import React, { useEffect, useState } from 'react'; import { api } from '../services/api.js'; import { usePoll } from '../hooks/usePoll.js'; import { Err } from '../components/ui.jsx'
const W = [['hook', 'Hook strength'], ['information', 'Information value'], ['emotion', 'Emotional intensity'], ['curiosity', 'Curiosity factor'], ['completeness', 'Story completeness'], ['engagement', 'Audio engagement'], ['independence', 'Context independence']]
const DEF = { hook: .2, information: .2, emotion: .15, curiosity: .15, completeness: .15, engagement: .1, independence: .05 }
export default function Settings() {
  const [h] = usePoll(api.health, 0); const [s, setS] = useState(null); const [msg, setMsg] = useState('')
  useEffect(() => { api.settings().then(x => setS({ chunk_seconds: 180, chunk_overlap: 30, min_clip_s: 15, max_clip_s: 90, weights: DEF, ...x })) }, [])
  if (!s) return <div className="text-slate-400">Loading…</div>
  const set = (k, v) => setS({ ...s, [k]: v }); const save = async () => { await api.saveSettings(s); setMsg('Saved. Applies to the next analysis.') }
  const hw = h?.hardware; const total = Object.values(s.weights).reduce((a, b) => a + b, 0)
  return (<div className="space-y-6 fade"><h1 className="text-2xl font-semibold text-white">Model Settings</h1>
    <div className="grid gap-4 sm:grid-cols-3"><div className="card p-4 text-sm"><div className="label">GPU</div>{hw?.gpu ? `${hw.gpu} · ${hw.vram_mb} MB · CUDA ${hw.cuda ? 'ready' : 'not ready (CPU fallback)'}` : 'None detected — CPU mode'}</div>
      <div className="card p-4 text-sm"><div className="label">FFmpeg</div>{hw?.ffmpeg ? 'Installed ✓' : 'Missing — winget install Gyan.FFmpeg'}</div>
      <div className="card p-4 text-sm"><div className="label">Ollama</div>{h?.ollama.ok ? `Running · ${h.ollama.models.length} models` : <span className="text-amber-300">{h?.ollama.error || '…'}</span>}</div></div>
    <div className="card space-y-4 p-6"><div className="flex flex-wrap gap-2">{Object.entries(h?.presets || {}).map(([k, v]) => <button key={k} className="btn-ghost capitalize" onClick={() => setS({ ...s, ...v })}>{k} preset</button>)}</div>
      <div className="grid gap-4 sm:grid-cols-3"><div><label className="label">Whisper model</label><select className="input" value={s.whisper_model} onChange={e => set('whisper_model', e.target.value)}>{['tiny', 'base', 'small', 'medium', 'large-v3'].map(m => <option key={m}>{m}</option>)}</select></div>
        <div><label className="label">Ollama model</label><input className="input" list="m" value={s.ollama_model} onChange={e => set('ollama_model', e.target.value)} /><datalist id="m">{h?.ollama.models?.map(m => <option key={m} value={m} />)}</datalist></div>
        <div><label className="label">Device</label><select className="input" value={s.device} onChange={e => set('device', e.target.value)}><option value="auto">Auto</option><option value="cuda">CUDA (GPU)</option><option value="cpu">CPU</option></select></div></div>
      <div className="grid gap-4 sm:grid-cols-4">{[['chunk_seconds', 'Chunk (s)'], ['chunk_overlap', 'Overlap (s)'], ['min_clip_s', 'Min clip (s)'], ['max_clip_s', 'Max clip (s)']].map(([k, l]) => <div key={k}><label className="label">{l}</label><input type="number" className="input" value={s[k]} onChange={e => set(k, +e.target.value)} /></div>)}</div>
      <p className="text-xs text-slate-500">With 4 GB VRAM keep Whisper ≤ small and an LLM ≤ 4B for GPU speed. Larger models will run slower via CPU spill-over.</p></div>
    <div className="card space-y-3 p-6"><div className="flex justify-between"><div className="text-sm font-medium text-white">Ranking weights</div><div className={`text-xs ${Math.abs(total - 1) < .02 ? 'text-slate-400' : 'text-amber-300'}`}>sum {total.toFixed(2)} (normalised automatically)</div></div>
      {W.map(([k, l]) => <div key={k} className="grid grid-cols-5 items-center gap-3 text-sm"><span className="col-span-2 text-slate-300">{l}</span><input className="col-span-2 accent-violet-500" type="range" min="0" max="0.5" step="0.01" value={s.weights[k]} onChange={e => set('weights', { ...s.weights, [k]: +e.target.value })} /><span className="text-right text-slate-400">{Math.round(s.weights[k] * 100)}%</span></div>)}</div>
    <div className="flex items-center gap-3"><button className="btn-primary" onClick={save}>Save settings</button><span className="text-sm text-slate-400">{msg}</span></div></div>)
}
