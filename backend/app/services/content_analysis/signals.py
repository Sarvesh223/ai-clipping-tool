"""Measured (non-LLM) signals: audio energy, scene changes/motion, and equal-part planning for speech-less videos."""
import math, re, subprocess, wave
import numpy as np

def has_audio(video) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    return bool(r.stdout.strip())

def is_speechless(tr, duration, min_wpm=15) -> bool:
    words = sum(len(s.words) or len(s.text.split()) for s in tr.segments)
    return duration > 0 and words / (duration / 60) < min_wpm

class AudioEnergy:
    """Per-second loudness (RMS) of the 16 kHz mono wav. Proxy for energetic/dynamic delivery, music drops, reactions."""
    def __init__(self, wav):
        rms = []
        with wave.open(str(wav), "rb") as w:
            while True:
                buf = w.readframes(16000 * 600)
                if not buf: break
                a = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0
                n = len(a) // 16000
                if n: rms.extend(np.sqrt((a[:n * 16000].reshape(n, 16000) ** 2).mean(axis=1)).tolist())
        self.rms = np.array(rms or [0.0]); self.ref = float(np.percentile(self.rms, 95)) + 1e-9
    def score(self, a, b) -> float:
        seg = self.rms[int(a):max(int(a) + 1, int(math.ceil(b)))]
        if not len(seg): return 0.0
        lvl = min(1.2, float(seg.mean()) / self.ref)
        dyn = min(1.0, (float(np.percentile(seg, 90)) - float(np.percentile(seg, 30))) / self.ref)
        return round(10 * min(1.0, 0.6 * lvl + 0.4 * dyn), 2)

def scene_series(video, fps=4):
    """(times, scene_score) sampled at `fps`; scene_score ~ how much the picture changed (cuts spike near 1)."""
    vf = f"fps={fps},scale=320:-2,select='gte(scene,0)',metadata=print:file=-"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an", "-vf", vf, "-f", "null", "-"],
                       capture_output=True, text=True)
    t, ts, sc = None, [], []
    for line in (r.stdout + "\n" + r.stderr).splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m: t = float(m.group(1))
        m = re.search(r"lavfi\.scene_score=([\d.]+)", line)
        if m and t is not None: ts.append(t); sc.append(float(m.group(1)))
    return np.array(ts), np.array(sc)

def plan_equal_parts(duration, cuts, lo=15.0, hi=25.0, target=20.0):
    """Equal-length parts inside [lo, hi] s. Each boundary is moved to the nearest real scene cut when that keeps
    every part inside the limits, so clips are not chopped mid-shot."""
    if duration <= hi: return [(0.0, float(duration))] if duration >= 1 else []
    viol = lambda k: max(0, lo - duration / k) + max(0, duration / k - hi)
    n = min(range(1, int(duration // 5) + 2), key=lambda k: (viol(k), abs(duration / k - target)))
    L, bounds, cuts = duration / n, [0.0], sorted(float(c) for c in cuts)
    for i in range(1, n):
        left, prev, ideal = n - i, bounds[-1], i * L
        lo_b, hi_b = max(prev + lo, duration - left * hi), min(prev + hi, duration - left * lo)
        if lo_b > hi_b: bounds.append(ideal); continue
        window = [c for c in cuts if lo_b <= c <= hi_b and abs(c - ideal) <= min(4.0, L * 0.2)]
        bounds.append(min(window, key=lambda c: abs(c - ideal)) if window else min(max(ideal, lo_b), hi_b))
    bounds.append(float(duration))
    return [(round(a, 2), round(b, 2)) for a, b in zip(bounds, bounds[1:])]

def score_parts(parts, ts, sc, cuts, energy=None):
    rows = []
    for a, b in parts:
        seg = sc[(ts >= a) & (ts < b)]
        motion = (float(seg.mean()) + 0.5 * float(np.percentile(seg, 90))) if len(seg) else 0.0
        dens = int(((cuts >= a) & (cuts < b)).sum()) / max(b - a, 1) * 10
        rows.append(dict(start=a, end=b, motion=motion, dynamics=dens, audio=energy.score(a, b) if energy else None))
    def norm(key):                      # relative to the other parts of THIS video, 0-10
        v = [r[key] for r in rows]; lo, hi = min(v), max(v)
        return [5.0 if hi - lo < 1e-9 else 10 * (x - lo) / (hi - lo) for x in v]
    m, d = norm("motion"), norm("dynamics"); au = norm("audio") if energy else [None] * len(rows)
    for r, mi, di, ai in zip(rows, m, d, au):
        raw = (0.45 * mi + 0.25 * di + 0.30 * ai) if ai is not None else (0.6 * mi + 0.4 * di)
        r["score"] = round(min(99, 30 + 7 * raw), 1); r["viral_pct"] = round(r["score"] * 0.85, 1)
        r["breakdown"] = {"motion": round(mi, 1), "dynamics": round(di, 1), **({"audio_energy": round(ai, 1)} if ai is not None else {})}
    return rows
