import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services.content_analysis.models import Transcript, Segment, Word
from app.services.content_analysis.analyzer import analyze
from app.services.content_analysis.chunker import make_chunks
from app.services.clip_ranking.scoring import rank
from app.services.clip_ranking.dedup import select_diverse
from app.services.clip_ranking.boundaries import optimize
from app.core.config import settings

SENTS = [
 "Most people think saving money is the secret to getting rich.",
 "That is completely wrong, and here is why it matters.",
 "I spent ten years studying wealthy founders and not one of them got there by saving.",
 "They did something different: they bought assets that grew while they slept.",
 "Let me give you a real example from my own life.",
 "In two thousand twelve I had four thousand dollars and no job.",
 "I put it all into a tiny rental property and everyone laughed at me.",
 "Three years later that property paid more per month than my old salary.",
 "So the lesson is simple: own things that pay you, do not just store cash.",
 "Now let's talk about something totally different, the weather in spring.",
 "Spring weather is usually mild and a bit rainy in most places really.",
 "um and then we went to the shop to buy some bread and stuff",
]
def build(n_repeat=6):
    segs, t = [], 0.0
    for r in range(n_repeat):
        for s in SENTS:
            words, cur = [], t
            for w in s.split():
                words.append(Word(cur, cur + 0.4, w)); cur += 0.4
            segs.append(Segment(t, cur, s, words)); t = cur + 0.3
    return Transcript(segs)

T = build()
good = T.segments[0]; end = T.segments[8]
def fake_llm(system, user):
    return {"candidates": [
      {"start": good.start, "end": end.end, "hook_quote": "Most people think saving money is the secret",
       "main_message": "Assets beat savings", "why": "Contrarian claim then proof", "target_audience": "Entrepreneurs",
       "titles": ["a","b","c","d","e"], "scores": {"hook": 9, "information": 8, "emotion": 6, "curiosity": 8, "completeness": 9, "independence": 8}},
      {"start": 9999.0, "end": 10040.0, "hook_quote": "invented", "scores": {"hook": 10}},          # fabricated timestamps
      {"start": good.start, "end": end.end, "hook_quote": "Aliens built the pyramids for fun and profit",  # fabricated quote
       "scores": {"hook": 10, "information": 10, "emotion": 10, "curiosity": 10, "completeness": 10, "independence": 10}},
      {"start": T.segments[9].start, "end": T.segments[11].end, "hook_quote": "Now let's talk",
       "scores": {"hook": 8, "emotion": 8, "curiosity": 8, "information": 8, "completeness": 8, "independence": 8}},
    ]}

def test_chunks_overlap_and_cover():
    ch = make_chunks(T, 120, 30)
    assert len(ch) > 1 and ch[0][0] is T.segments[0] and ch[-1][-1] is T.segments[-1]
    assert ch[1][0].start < ch[0][-1].end                    # overlap

def test_pipeline():
    settings.min_clip_s = 15
    c = analyze(T, llm=fake_llm)
    assert all(x.end <= T.duration and x.start >= 0 for x in c)
    assert not any(x.start > 5000 for x in c)                 # fabricated timestamps rejected
    assert all("pyramids" not in x.hook for x in c)           # fabricated quote dropped
    ranked = rank(T, c)
    assert ranked[0].start < 5 and ranked[0].score > ranked[-1].score
    picked, method = select_diverse(T, ranked, 10)
    spans = [(p.start, p.end) for p in picked]
    for i, a in enumerate(spans):
        for b in spans[i+1:]: assert min(a[1], b[1]) - max(a[0], b[0]) <= 0
    from app.services.clip_ranking.boundaries import optimize_all
    final = optimize_all(T, picked)
    fs = sorted(final, key=lambda c: c.start)
    for a, b in zip(fs, fs[1:]): assert a.end <= b.start
    for f in final: assert f.end > f.start
    print("method:", method)
    for f in final: print(f"{f.start:7.2f}-{f.end:7.2f} score={f.score} pen={f.penalties} hook={f.hook[:50]!r}")

if __name__ == "__main__":
    test_chunks_overlap_and_cover(); test_pipeline(); print("ALL PASSED")

def test_line_number_selection_and_funnel():
    seen = []
    def llm(system, user):
        seen.append(user)
        return {"candidates": [
          {"start_line": 0, "end_line": 8, "hook_quote": "Most people think saving", "scores": {"hook": 9, "information": 8, "completeness": 9}},
          {"start_line": 0, "end_line": 1, "scores": {"hook": 7}},            # too short -> extended to real following lines
          {"start_line": 5000, "end_line": 5003, "scores": {"hook": 10}},     # line numbers that do not exist -> rejected
          {"start_line": "x"},                                                # malformed -> rejected
        ]}
    st = {}
    c = analyze(T, llm=llm, stats=st)
    k = st["chunks"]; assert k >= 2
    assert "[0] (" in seen[0] and "[1] (" in seen[0]                          # numbered lines reach the model
    assert st["raw"] == 4 * k and st["rejected"].get("line_number_not_in_transcript") == k and st["rejected"].get("bad_fields") == k
    starts = {x.start for x in c}; assert starts == {T.segments[0].start}     # both valid picks merged into one
    seg_ends = {s.end for s in T.segments}
    assert all(x.end in seg_ends for x in c)                                  # every end is a real segment boundary
    assert all(x.duration >= 15 * 0.6 for x in c)
    print("funnel:", st)

if __name__ == "__main__":
    test_line_number_selection_and_funnel(); print("LINE-NUMBER TESTS PASSED")
