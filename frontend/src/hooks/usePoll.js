import { useEffect, useRef, useState, useCallback } from 'react'
export function usePoll(fn, ms = 2000, deps = []) {
  const [data, setData] = useState(null); const [err, setErr] = useState(null); const alive = useRef(true)
  const load = useCallback(async () => { try { const d = await fn(); if (alive.current) { setData(d); setErr(null) } } catch (e) { if (alive.current) setErr(e.message) } }, deps)
  useEffect(() => { alive.current = true; load(); const t = ms && setInterval(load, ms); return () => { alive.current = false; clearInterval(t) } }, [load, ms])
  return [data, err, load]
}
