"""PASS 2: overlapping contextual chunks, cut on segment boundaries."""
from typing import List
from .models import Transcript, Segment

def make_chunks(t: Transcript, size: float, overlap: float) -> List[List[Segment]]:
    segs, chunks, i = t.segments, [], 0
    while i < len(segs):
        j = i + 1
        while j < len(segs) and segs[j].end - segs[i].start <= size: j += 1
        chunks.append(segs[i:j])
        if j >= len(segs): break
        k = j - 1                      # walk back until ~overlap seconds are shared
        while k > i + 1 and segs[j - 1].end - segs[k - 1].start <= overlap: k -= 1
        i = k if k > i else j
    return chunks

def render_chunk(chunk: List[Segment], idx=None) -> str:
    """idx: {id(segment): global line number}. Numbered lines let the LLM pick clips without copying floats."""
    if idx is None: return "\n".join(f"[{s.start:.2f}-{s.end:.2f}] {s.text.strip()}" for s in chunk)
    return "\n".join(f"[{idx[id(s)]}] ({s.start:.0f}s) {s.text.strip()}" for s in chunk)
