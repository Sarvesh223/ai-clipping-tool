"""PASS 2-5 orchestration: chunk -> LLM -> validate -> merge. LLM call is injectable for testing."""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional
from .models import Transcript, Candidate
from .chunker import make_chunks, render_chunk
from .prompts import SYSTEM, user_prompt
from .validation import check_candidate
from collections import Counter
from . import llm_client
from ...core.config import settings

def merge_candidates(cands: List[Candidate], iou_thr=0.5) -> List[Candidate]:
    out: List[Candidate] = []
    for c in sorted(cands, key=lambda x: x.start):
        for m in out:
            inter = max(0, min(m.end, c.end) - max(m.start, c.start))
            union = max(m.end, c.end) - min(m.start, c.start)
            if union and inter / union >= iou_thr:
                keep = m if sum(m.llm_scores.values()) >= sum(c.llm_scores.values()) else c
                m.start, m.end = (keep.start, keep.end)
                for f in ("hook","main_message","why","audience","titles","title","caption","edit_style","category","llm_scores"):
                    setattr(m, f, getattr(keep, f))
                m.sources += 1; break
        else: out.append(c)
    return out

def analyze(t: Transcript, audience="General audience", style="Educational",
            llm: Optional[Callable[[str, str], dict]] = None, workers=1, progress=None, stats: Optional[dict] = None) -> List[Candidate]:
    llm = llm or (lambda sys, usr: llm_client.chat_json(settings.ollama_url, settings.ollama_model, sys, usr))
    chunks = make_chunks(t, settings.chunk_seconds, settings.chunk_overlap)
    idx = {id(s): i for i, s in enumerate(t.segments)}; rejected = Counter(); raw_n = [0]
    def run(ch):
        text = render_chunk(ch, idx)
        import time; t0 = time.time(); data = None; last = ""
        for attempt in (1, 2):                              # one retry: transient stalls / invalid JSON happen with small models
            try:
                data = llm(SYSTEM, user_prompt(text, settings.min_clip_s, settings.max_clip_s,
                                               settings.max_candidates_per_chunk, audience, style)); break
            except Exception as e:
                last = str(e); print(f"[analyze] chunk attempt {attempt} failed: {last}")
        if data is None: return [], last
        print(f"[analyze] chunk done in {time.time() - t0:.0f}s, {len(data.get('candidates') or [])} raw candidates")
        good = []
        for r in (data.get("candidates") or []):
            raw_n[0] += 1
            if not isinstance(r, dict): rejected["not_an_object"] += 1; continue
            c, why = check_candidate(r, t, settings.snap_tolerance_s, settings.min_clip_s, settings.max_clip_s)
            if c: good.append(c)
            else: rejected[why] += 1
        return good, None
    found, errors, done = [], [], 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for good, err in ex.map(run, chunks):
            found += good; done += 1
            if err: errors.append(err)
            if progress: progress(done, len(chunks))        # real progress: chunks completed / total
    if errors and not found:
        raise llm_client.OllamaError(f"All {len(chunks)} chunks failed. First error: {errors[0]}")
    merged = merge_candidates(found)
    if stats is not None:
        stats.update(chunks=len(chunks), failed_chunks=len(errors), raw=raw_n[0], valid=len(found), rejected=dict(rejected), merged=len(merged))
    print(f"[analyze] funnel: chunks={len(chunks)} raw={raw_n[0]} valid={len(found)} rejected={dict(rejected)} merged={len(merged)}")
    return merged
