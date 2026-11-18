"""PASS 6-7: scoring. Final = weighted LLM dimensions (+ measured transcript signals) minus context penalties."""
import re
from typing import List
from ..content_analysis.models import Transcript, Candidate
from ...core.config import settings

FILLERS = {"and","so","but","um","uh","like","well","yeah","because","or","then","also","anyway"}
DEPENDENT = {"he","she","they","it","this","that","those","these","him","her","them"}

def _words(t: Transcript, a, b):
    return [w for s in t.segments if s.end > a and s.start < b for w in s.words if a <= w.start < b]

def engagement_signal(t: Transcript, c: Candidate, energy=None) -> float:
    """0-10 audio-engagement proxy from measured speech: pace, pace variation, questions/exclamations.
    (Visual engagement requires the video stage; see README limitations.)"""
    txt = t.text_between(c.start, c.end)
    words = _words(t, c.start, c.end)
    wps = len(words) / max(c.duration, 1)
    pace = 10 - min(10, abs(wps - 2.8) * 3.5)           # ~2.8 words/s is lively conversational speech
    punct = min(10, (txt.count("?") + txt.count("!")) * 2.5)
    speech = 0.7 * pace + 0.3 * punct
    return round(0.5 * speech + 0.5 * energy(c.start, c.end), 2) if energy else round(speech, 2)

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

def score_candidate(t: Transcript, c: Candidate, weights=None, energy=None) -> Candidate:
    w = weights or settings.weights
    dims = dict(c.llm_scores); dims["viral"] = dims.pop("viral_potential", 0.0)
    dims["engagement"] = engagement_signal(t, c, energy)
    total_w = sum(w.values()) or 1
    base = sum(w[k] * dims.get(k, 0) * 10 for k in w) / total_w   # 0-100 weighted quality
    pen = penalties(t, c); c.penalties = pen; ps = sum(pen.values())
    c.score_breakdown = {k: round(dims.get(k, 0), 2) for k in w}
    bonus = min(4, (c.sources - 1) * 2)    # multi-chunk agreement: mild, capped
    c.quality = max(0, min(99, base - ps + bonus))
    # Viral potential: shareability/retention/curiosity/emotion/hook + measured energy. An ESTIMATE, not a prediction.
    v = (0.28 * dims["viral"] + 0.20 * dims.get("shareability", 0) + 0.14 * dims.get("retention", 0) + 0.12 * dims.get("hook", 0)
         + 0.10 * dims.get("curiosity", 0) + 0.08 * dims.get("emotion", 0) + 0.08 * dims["engagement"]) * 10
    c.viral_pct = round(max(0, min(97, v - 0.6 * ps)), 1)
    c.score = round(max(0, min(99, 0.6 * c.quality + 0.4 * c.viral_pct)), 1)   # ranking = quality AND viral potential
    c.quality = round(c.quality, 1)
    return c

def rank(t: Transcript, cands: List[Candidate], weights=None, energy=None) -> List[Candidate]:
    return sorted((score_candidate(t, c, weights, energy) for c in cands), key=lambda c: -c.score)
