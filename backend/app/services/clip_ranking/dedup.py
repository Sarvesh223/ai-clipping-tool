"""Duplicate/overlap removal using semantic embeddings (sentence-transformers) with a TF-IDF fallback."""
import math, re
from collections import Counter
from typing import List
from ..content_analysis.models import Transcript, Candidate

def _tfidf(texts):
    docs = [re.findall(r"[a-z']{3,}", x.lower()) for x in texts]
    df = Counter(w for d in docs for w in set(d)); n = len(docs)
    vecs = []
    for d in docs:
        tf = Counter(d)
        vecs.append({w: c * (math.log((1 + n) / (1 + df[w])) + 1) for w, c in tf.items()})
    return vecs

def _cos_sparse(a, b):
    num = sum(v * b.get(k, 0) for k, v in a.items())
    den = math.sqrt(sum(v*v for v in a.values())) * math.sqrt(sum(v*v for v in b.values()))
    return num / den if den else 0.0

def similarity_matrix(texts: List[str]):
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        m = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        e = m.encode(texts, normalize_embeddings=True)
        return (e @ e.T).tolist(), "embeddings"
    except Exception:
        v = _tfidf(texts)
        return [[_cos_sparse(a, b) for b in v] for a in v], "tfidf"

def select_diverse(t: Transcript, ranked: List[Candidate], limit: int, sim_thr=0.72, max_overlap=0.2):
    texts = [t.text_between(c.start, c.end) for c in ranked]
    sim, method = similarity_matrix(texts) if ranked else ([], "none")
    chosen: List[int] = []
    for i, c in enumerate(ranked):
        ok = True
        for j in chosen:
            o = ranked[j]
            inter = max(0, min(c.end, o.end) - max(c.start, o.start))
            if inter / max(min(c.duration, o.duration), 1) > max_overlap or sim[i][j] >= sim_thr:
                ok = False; break
        if ok: chosen.append(i)
        if len(chosen) >= limit: break
    return [ranked[i] for i in chosen], method

def target_count(duration_s: float) -> int:
    return max(10, min(30, int(duration_s // 180) + 8)) if duration_s > 0 else 10
