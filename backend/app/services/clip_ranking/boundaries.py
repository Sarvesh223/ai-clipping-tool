"""PASS 8: snap to sentence boundaries using word timestamps, trim lead-in filler, add natural padding."""
from ..content_analysis.models import Transcript, Candidate
from ...core.config import settings

LEAD_FILLERS = {"um","uh","so","and","but","well","like","yeah","okay"}

def optimize(t: Transcript, c: Candidate, pad_in=0.15, pad_out=0.35) -> Candidate:
    words = [w for s in t.segments for w in s.words]
    segs = t.segments
    if words:
        inside = [w for w in words if c.start - 0.01 <= w.start < c.end]
        while len(inside) > 5 and inside[0].text.strip(" ,.").lower() in LEAD_FILLERS:
            inside = inside[1:]
        if inside: c.start = inside[0].start
        # end on last word that terminates a sentence if one exists in the final 25%
        tail = [w for w in inside if w.start > c.start + 0.75 * (c.end - c.start)]
        ends = [w for w in tail if w.text.strip()[-1:] in ".?!"]
        c.end = ends[-1].end if ends else (inside[-1].end if inside else c.end)
    # never run into the neighbouring speech: clamp padding to gaps
    prev_end = max([s.end for s in segs if s.end <= c.start] or [0.0])
    next_start = min([s.start for s in segs if s.start >= c.end] or [t.duration + pad_out])
    c.start = max(prev_end + 0.02 if prev_end < c.start else c.start, c.start - pad_in)
    c.end = min(next_start - 0.02 if next_start > c.end else c.end, c.end + pad_out)
    if c.duration > settings.max_clip_s:                      # shrink back to nearest earlier sentence end
        cut = c.start + settings.max_clip_s
        ends = [w.end for w in words if c.start < w.end <= cut and w.text.strip()[-1:] in ".?!"]
        if ends: c.end = ends[-1]
    c.start, c.end = round(c.start, 2), round(c.end, 2)
    return c

def optimize_all(t: Transcript, cands):
    """Optimize each clip, then guarantee no two final clips overlap after padding."""
    out = sorted((optimize(t, c) for c in cands), key=lambda c: c.start)
    for a, b in zip(out, out[1:]):
        if a.end > b.start:
            mid = round((a.end + b.start) / 2, 2); a.end, b.start = min(a.end, mid), max(b.start, mid)
    return sorted(out, key=lambda c: -c.score)
