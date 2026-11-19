"""FAST mode. 1) build clip windows on real sentence boundaries and score them with cheap heuristics (milliseconds),
2) keep the best non-overlapping ~30, 3) ask the LLM ONLY for short score ratings in small batches, 4) write titles for the final top clips.
Timestamps come from real transcript segments, so nothing can be fabricated. Far fewer LLM tokens than scanning every chunk."""
import re
from typing import Callable, List, Optional
from .models import Transcript, Candidate
from . import llm_client
from ..clip_ranking.scoring import penalties
from ...core.config import settings

HOOK = re.compile(r"\b(secret|never|always|worst|best|biggest|mistake|truth|nobody|everyone|why|how|stop|actually|wrong|crazy|insane|shocking|free|million|billion|first|only|nobody|lie)\b", re.I)
EMO = re.compile(r"\b(love|hate|afraid|fear|angry|cry|cried|laugh|funny|proud|ashamed|heart|death|lost|won|fail|failed|struggle|amazing|terrible|incredible)\b", re.I)
CURIO = re.compile(r"\b(here's|here is|let me tell|you won't believe|the reason|turns out|what if|imagine|the thing is|but then)\b", re.I)
_end = lambda s: s.strip()[-1:] in ".?!"

def build_windows(t: Transcript, lo: float, hi: float) -> List[Candidate]:
    segs, n, out = t.segments, len(t.segments), []
    for strict in (True, False):                                  # fall back to any boundary if Whisper gave no punctuation
        for i in range(n):
            if strict and i and not _end(segs[i - 1].text): continue
            ends = [j for j in range(i, n) if lo * 0.8 <= segs[j].end - segs[i].start <= hi and (not strict or _end(segs[j].text))]
            for j in sorted({ends[0], ends[-1]} if ends else []):
                out.append(Candidate(start=segs[i].start, end=segs[j].end))
        if out: break
    return out

def heuristic(t: Transcript, c: Candidate, energy=None):
    segs = [s for s in t.segments if s.end > c.start and s.start < c.end]
    first = segs[0].text if segs else ""; text = t.text_between(c.start, c.end)
    hook = min(10, (3 if first.strip().endswith("?") else 0) + min(4, 1.5 * len(HOOK.findall(first)))
               + (2 if re.search(r"\d", first) else 0) + (1 if re.search(r"\b(you|your)\b", first, re.I) else 0))
    d = dict(hook=hook, emotion=min(10, 2 * len(EMO.findall(text)) + text.count("!")),
             curiosity=min(10, 2.5 * len(CURIO.findall(text)) + 1.5 * text.count("?")),
             information=min(10, len(re.findall(r"\d+", text)) + len(text.split()) / 25),
             energy=energy(c.start, c.end) if energy else 5.0)
    pen = sum(penalties(t, c).values()) / 10
    c.heur = max(0.0, 0.30 * d["hook"] + 0.15 * d["emotion"] + 0.20 * d["curiosity"] + 0.15 * d["information"] + 0.20 * d["energy"] - 0.8 * pen)
    return d

def nms(cands, k, max_overlap=0.2):
    chosen = []
    for c in sorted(cands, key=lambda x: -x.heur):
        if all(max(0, min(c.end, o.end) - max(c.start, o.start)) / max(min(c.duration, o.duration), 1) <= max_overlap for o in chosen):
            chosen.append(c)
        if len(chosen) >= k: break
    return chosen

SYS_RATE = """You rate short-video clip candidates for social media. Be critical: most clips are 3-6 out of 10.
For EACH clip return scores 0-10: hook, information, emotion, curiosity, completeness (ends on a finished thought),
independence (understandable alone), shareability, retention (pays off), viral_potential; plus category (one word) and why (max 12 words).
Return JSON only: {"ratings":[{"id":int,"hook":..,"information":..,"emotion":..,"curiosity":..,"completeness":..,"independence":..,"shareability":..,"retention":..,"viral_potential":..,"category":str,"why":str}]}"""
SYS_TITLE = """Write social-media titles for each clip. Never invent facts that are not in the text.
Return JSON only: {"clips":[{"id":int,"titles":[5 short titles],"caption":str,"editing_style":str}]}"""
DIMS = ("hook", "information", "emotion", "curiosity", "completeness", "independence", "shareability", "retention", "viral_potential")

def _snip(text, n=650): return text if len(text) <= n else text[:n * 2 // 3] + " ... " + text[-n // 3:]
def _default_llm(sys_, usr): return llm_client.chat_json(settings.ollama_url, settings.ollama_model, sys_, usr)

def analyze_fast(t, audience="General audience", style="Educational", llm=None, energy=None, k=24, batch=6, stats=None, progress=None):
    llm = llm or _default_llm
    wins = build_windows(t, settings.min_clip_s, settings.max_clip_s)
    dims = {}
    for c in wins: dims[id(c)] = heuristic(t, c, energy)
    top = nms(wins, k)
    failed = 0
    for b0 in range(0, len(top), batch):
        grp = top[b0:b0 + batch]
        usr = f"Audience: {audience}. Style: {style}.\nCLIPS:\n" + "\n".join(f"#{i} ({c.duration:.0f}s): {_snip(t.text_between(c.start, c.end))}" for i, c in enumerate(grp))
        try:
            rated = {int(r["id"]): r for r in (llm(SYS_RATE, usr).get("ratings") or []) if isinstance(r, dict) and "id" in r}
        except Exception as e:
            print("[fast] rerank batch failed:", e); rated = {}
        for i, c in enumerate(grp):
            r = rated.get(i)
            if r:
                c.llm_scores = {d: max(0.0, min(10.0, float(r.get(d, 0) or 0))) for d in DIMS}
                c.why, c.category = str(r.get("why", "")), str(r.get("category", ""))
            else:                                                   # LLM unavailable for this clip: heuristic-derived scores, clearly weaker
                failed += 1; h = dims[id(c)]
                c.llm_scores = dict(hook=h["hook"], information=h["information"], emotion=h["emotion"], curiosity=h["curiosity"],
                                    completeness=4, independence=4, shareability=3, retention=3, viral_potential=3)
                c.why = "Selected by heuristics (AI rating unavailable)"
            first = next((s.text.strip() for s in t.segments if s.end > c.start), "")
            c.hook = first[:200]; c.title = first[:60]
        if progress: progress(min(b0 + batch, len(top)), len(top))      # real: clips rated / total
    if stats is not None: stats.update(mode="fast", windows=len(wins), shortlisted=len(top), rerank_failed=failed)
    print(f"[fast] windows={len(wins)} shortlisted={len(top)} rerank_failed={failed}")
    return top

def add_titles(clips, t, audience, style, llm=None, n=10, batch=5):
    llm = llm or _default_llm; clips = clips[:n]
    for b0 in range(0, len(clips), batch):
        grp = clips[b0:b0 + batch]
        usr = f"Audience: {audience}. Style: {style}.\nCLIPS:\n" + "\n".join(f"#{i}: {_snip(t.text_between(c.start, c.end), 500)}" for i, c in enumerate(grp))
        try: res = {int(r["id"]): r for r in (llm(SYS_TITLE, usr).get("clips") or []) if isinstance(r, dict) and "id" in r}
        except Exception as e: print("[fast] title batch failed:", e); continue
        for i, c in enumerate(grp):
            r = res.get(i)
            if r:
                c.titles = [str(x) for x in (r.get("titles") or [])][:5]; c.title = c.titles[0] if c.titles else c.title
                c.caption, c.edit_style = str(r.get("caption", "")), str(r.get("editing_style", ""))
