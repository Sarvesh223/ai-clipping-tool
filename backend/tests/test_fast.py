import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_pipeline import build
from app.services.content_analysis import fast_analyzer as fa, analyzer
from app.services.clip_ranking.scoring import rank
from app.services.clip_ranking.dedup import select_diverse, target_count
from app.services.clip_ranking.boundaries import optimize_all
from app.core.config import settings
import json

def run():
    T = build(40)                                   # ~40 min of speech, ~480 segments
    print(f"transcript: {T.duration/60:.0f} min, {len(T.segments)} segments")
    calls = {"fast": 0, "old": 0}
    def llm_fast(sysm, usr):
        calls["fast"] += 1
        if "rate short-video" in sysm:
            n = usr.count("\n#") + usr.count("CLIPS:\n#")
            ids = range(usr.count("#"))
            return {"ratings": [dict(id=i, hook=7, information=6, emotion=5, curiosity=6, completeness=8, independence=7,
                    shareability=6, retention=6, viral_potential=5, category="finance", why="clear claim then proof") for i in ids]}
        ids = range(usr.count("#"))
        return {"clips": [dict(id=i, titles=[f"t{i}-{j}" for j in range(5)], caption="c", editing_style="fast cuts") for i in ids]}
    t0 = time.time(); st = {}
    cands = fa.analyze_fast(T, llm=llm_fast, k=min(30, int(target_count(T.duration) * 1.3)), stats=st)
    ranked = rank(T, cands); picked, _ = select_diverse(T, ranked, target_count(T.duration)); final = optimize_all(T, picked)
    fa.add_titles(final, T, "General", "Educational", llm=llm_fast)
    dt = time.time() - t0
    print(f"FAST: {len(final)} clips, {calls['fast']} LLM calls, {dt:.2f}s non-LLM time", st)
    segs = {round(s.start, 2) for s in T.segments}
    assert all(c.title and len(c.titles) == 5 for c in final[:10])
    assert all(settings.min_clip_s * 0.6 <= c.duration <= settings.max_clip_s * 1.3 for c in final)
    # old method LLM call count on the same transcript
    def llm_old(s, u): calls["old"] += 1; return {"candidates": []}
    analyzer.analyze(T, llm=llm_old)
    print(f"OLD full scan would make {calls['old']} LLM calls, each generating long JSON (5 titles, why, caption per candidate)")
    assert calls["fast"] <= calls["old"] + 6
if __name__ == "__main__": run(); print("FAST TESTS PASSED")
