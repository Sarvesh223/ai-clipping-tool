"""PASS 6-7: scoring. Final = weighted LLM dimensions (+ measured transcript signals) minus context penalties."""
import re
from typing import List
from ..content_analysis.models import Transcript, Candidate
from ...core.config import settings

FILLERS = {"and","so","but","um","uh","like","well","yeah","because","or","then","also","anyway"}
DEPENDENT = {"he","she","they","it","this","that","those","these","him","her","them"}

def _words(t: Transcript, a, b):
    return [w for s in t.segments if s.end > a and s.start < b for w in s.words if a <= w.start < b]

def engagement_signal(t: Transcript, c: Candidate) -> float:
    """0-10 audio-engagement proxy from measured speech: pace, pace variation, questions/exclamations.
    (Visual engagement requires the video stage; see README limitations.)"""
    txt = t.text_between(c.start, c.end)
    words = _words(t, c.start, c.end)
    wps = len(words) / max(c.duration, 1)
    pace = 10 - min(10, abs(wps - 2.8) * 3.5)           # ~2.8 words/s is lively conversational speech
    punct = min(10, (txt.count("?") + txt.count("!")) * 2.5)
    return round(0.7 * pace + 0.3 * punct, 2)

def penalties(t: Transcript, c: Candidate) -> dict:
    p = {}
    txt = t.text_between(c.start, c.end).strip()
    toks = re.findall(r"[a-z']+", txt.lower())
    if not toks: return {"empty": 100}
    segs = [s for s in t.segments if s.end > c.start and s.start < c.end]
    first = segs[0].text.strip() if segs else ""
    if first and first[0].islower(): p["incomplete_opening"] = 8
    if txt[-1] not in ".?!\"'": p["abrupt_ending"] = 10
    if toks[0] in FILLERS: p["weak_opening"] = 6
    if toks[0] in DEPENDENT: p["missing_context"] = 8
    gaps = [b.start - a.end for a, b in zip(segs, segs[1:]) if b.start - a.end > 1.5]
    if gaps: p["long_pauses"] = min(10, 2 + 2 * len(gaps) + sum(gaps))
    tri = [tuple(toks[i:i+3]) for i in range(len(toks) - 2)]
    if tri:
        rep = 1 - len(set(tri)) / len(tri)
        if rep > 0.15: p["repetition"] = round(min(12, rep * 40), 1)
    if c.duration > settings.max_clip_s: p["too_long"] = 8
    if c.duration < settings.min_clip_s: p["too_short"] = 10
    if len(toks) / max(c.duration, 1) < 1.2: p["sparse_speech"] = 5
    if re.search(r"\b(as i (said|mentioned)|like i said|going back to|earlier)\b", txt.lower()[:300]):
        p["needs_explanation"] = 6
    return p

def score_candidate(t: Transcript, c: Candidate, weights=None) -> Candidate:
    w = weights or settings.weights
    dims = dict(c.llm_scores); dims["engagement"] = engagement_signal(t, c)
    total_w = sum(w.values()) or 1
    base = sum(w[k] * dims.get(k, 0) * 10 for k in w) / total_w   # 0-100
    pen = penalties(t, c)
    c.penalties = pen
    c.score_breakdown = {k: round(dims.get(k, 0), 2) for k in w}
    # multi-chunk agreement is mild evidence the moment stands out (capped bonus)
    bonus = min(4, (c.sources - 1) * 2)
    c.score = round(max(0, min(99, base - sum(pen.values()) + bonus)), 1)  # never 100: estimate, not a guarantee
    return c

def rank(t: Transcript, cands: List[Candidate], weights=None) -> List[Candidate]:
    return sorted((score_candidate(t, c, weights) for c in cands), key=lambda c: -c.score)
