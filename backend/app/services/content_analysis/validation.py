"""Anti-hallucination: every LLM timestamp/quote is checked against the real transcript."""
import difflib
from typing import Optional
from .models import Transcript, Candidate

def _norm(s): return " ".join("".join(c.lower() if c.isalnum() or c == " " else " " for c in s).split())

def check_candidate(raw, t: Transcript, tol, lo, hi):
    """Returns (Candidate|None, reject_reason). Timestamps always come from real transcript segments."""
    segs = t.segments; n = len(segs)
    if not n: return None, "empty_transcript"
    try:
        if "start_line" in raw:
            sl, el = int(raw["start_line"]), int(raw["end_line"])
            if not (0 <= sl < n and 0 <= el < n): return None, "line_number_not_in_transcript"
            if el < sl: sl, el = el, sl
        else:                                           # legacy: snap float timestamps to segment boundaries
            a, b = float(raw["start"]), float(raw["end"])
            sl = min(range(n), key=lambda i: abs(segs[i].start - a)); el = min(range(n), key=lambda i: abs(segs[i].end - b))
            if abs(segs[sl].start - a) > tol or abs(segs[el].end - b) > tol: return None, "timestamp_not_in_transcript"
            if el < sl: return None, "bad_order"
    except (KeyError, TypeError, ValueError):
        return None, "bad_fields"
    while segs[el].end - segs[sl].start < lo and el + 1 < n: el += 1       # too short: extend to following real sentences
    while segs[el].end - segs[sl].start > hi * 1.15 and el > sl: el -= 1   # too long: trim back to a real boundary
    sa, eb = segs[sl].start, segs[el].end
    if eb - sa < lo * 0.6: return None, "too_short"
    return _build(raw, t, sa, eb), ""

def validate_candidate(raw, t, tol, lo, hi):
    return check_candidate(raw, t, tol, lo, hi)[0]

def _build(raw, t, sa, eb):
    text = t.text_between(sa, eb)
    hook = str(raw.get("hook_quote", "")).strip()
    if hook:                                                      # quote must really be in the clip opening
        opening = _norm(t.text_between(sa, min(eb, sa + 20)))
        h = _norm(hook)
        if h and h not in opening:
            m = difflib.SequenceMatcher(None, h, opening).find_longest_match(0, len(h), 0, len(opening))
            if m.size < 0.8 * len(h): hook = ""                   # discard fabricated quote, keep real opening
    if not hook:
        first = t.text_between(sa, sa + 0.01) or text
        hook = first.split(". ")[0][:200]
    sc = raw.get("scores", {}) or {}
    clean = {k: max(0.0, min(10.0, float(sc.get(k, 0) or 0))) for k in
             ("hook", "information", "emotion", "curiosity", "completeness", "independence", "shareability", "retention", "viral_potential")}
    titles = [str(x) for x in (raw.get("titles") or [])][:5]
    return Candidate(start=sa, end=eb, hook=hook, main_message=str(raw.get("main_message", "")),
        why=str(raw.get("why", "")), audience=str(raw.get("target_audience", "")),
        titles=titles, title=titles[0] if titles else hook[:60], caption=str(raw.get("caption", "")),
        edit_style=str(raw.get("editing_style", "")), category=str(raw.get("category", "")), llm_scores=clean)
