"""Persistent, resumable pipeline. Stages write real progress (done/total) or null when unknown."""
import json, threading, time, queue, traceback
from pathlib import Path
from ..database import db
from ..core.config import settings, DEFAULT_WEIGHTS
from ..core.paths import PROCESSED
from ..services.downloader import ytdlp_service as dl
from ..services.transcription import whisper_service as ws
from ..services.content_analysis.analyzer import analyze
from ..services.content_analysis import llm_client, signals as sig
from ..services.content_analysis.models import Transcript
from ..services.clip_ranking.scoring import rank
from ..services.clip_ranking.dedup import select_diverse, target_count
from ..services.clip_ranking.boundaries import optimize_all
from ..services.video_editor.render import render_clip
from ..services.thumbnail_generator.thumbs import thumbnails

STAGES = ["downloading", "extracting_audio", "transcribing", "understanding", "ranking", "rendering", "completed"]
_q: "queue.Queue[int]" = queue.Queue(); _cancel: set = set()

def apply_settings():
    s = db.get_settings()
    for k in ("ollama_model", "chunk_seconds", "chunk_overlap", "min_clip_s", "max_clip_s"):
        if k in s: setattr(settings, k, s[k])
    if "weights" in s: settings.weights = {**DEFAULT_WEIGHTS, **s["weights"]}
    return s

def stage(pid, name, done=None, total=None): db.update("projects", pid, stage=name, done=done, total=total, status="running")
def enqueue(pid): db.update("projects", pid, status="queued", error=None); _q.put(pid)
def cancel(pid): _cancel.add(pid)

def _wav(video, work):
    wav = work / "audio.wav"
    if not wav.exists(): ws.extract_audio(video, str(wav))
    return wav

def _insert(pid, start, end, score, title, data):
    return db.run("INSERT INTO clips(project_id,start,end,score,title,data) VALUES(?,?,?,?,?,?)", (pid, start, end, score, title, json.dumps(data)))

def _plan_visual(pid, video, work, duration, audio):
    """No usable speech: equal 15-25 s parts, boundaries snapped to scene cuts, ranked by motion/cuts/audio energy."""
    stage(pid, "understanding")                      # scene analysis (no exact progress available -> indeterminate bar)
    ts, sc = sig.scene_series(video)
    cuts = ts[sc > 0.35] if len(ts) else ts
    energy = sig.AudioEnergy(_wav(video, work)) if audio else None
    stage(pid, "ranking")
    rows = sig.score_parts(sig.plan_equal_parts(duration, cuts, settings.min_clip_s if settings.min_clip_s <= 25 else 15, 25), ts, sc, cuts, energy)
    ids = []
    for i, r in enumerate(rows, 1):
        why = ("Visual-only video (no speech detected): split into equal parts at scene boundaries. "
               "Ranked by on-screen motion, cut density" + (" and audio energy." if energy else "."))
        ids.append(_insert(pid, r["start"], r["end"], r["score"], f"Part {i}", dict(hook="", main_message="Visual segment",
                   why=why, audience="", titles=[], category="visual", breakdown=r["breakdown"], penalties={}, viral_pct=r["viral_pct"],
                   quality=r["score"], mode="visual_split", language="none")))
    f = dict(mode="visual_split", video_s=round(duration), parts=len(rows), scene_cuts=int(len(cuts)), final=len(rows))
    db.set_setting(f"funnel_{pid}", f); print("[pipeline] visual split:", f)
    return ids

def _analyze_speech(pid, p, video, work, tr, lang, chk):
    stage(pid, "understanding")                      # Whisper is freed; now the LLM gets the VRAM
    llm_client.check_ollama(settings.ollama_url, settings.ollama_model)
    funnel = {}
    cands = analyze(tr, p["audience"], p["style"], workers=1, stats=funnel, progress=lambda d, t: db.update("projects", pid, done=d, total=t))
    if chk(): raise RuntimeError("cancelled")
    stage(pid, "ranking")
    try: energy = sig.AudioEnergy(_wav(video, work)).score
    except Exception as e: print("[pipeline] audio energy unavailable:", e); energy = None
    ranked = rank(tr, cands, energy=energy)
    picked, method = select_diverse(tr, ranked, target_count(tr.duration), settings.dup_similarity)
    final = optimize_all(tr, picked)
    funnel.update(ranked=len(ranked), dropped_as_duplicates=len(ranked) - len(picked), final=len(final), video_s=round(tr.duration))
    db.set_setting(f"funnel_{pid}", funnel); print("[pipeline] funnel:", funnel)
    return [_insert(pid, c.start, c.end, c.score, c.title, dict(hook=c.hook, main_message=c.main_message, why=c.why,
            audience=c.audience, titles=c.titles, caption=c.caption, edit_style=c.edit_style, category=c.category,
            breakdown=c.score_breakdown, penalties=c.penalties, viral_pct=c.viral_pct, quality=c.quality,
            language=lang, dedup=method, mode="speech")) for c in final]

def run_project(pid):
    p = db.one("SELECT * FROM projects WHERE id=?", (pid,)); apply_settings()
    cfg = db.get_settings(); work = PROCESSED / str(pid); work.mkdir(exist_ok=True)
    db.update("projects", pid, started=time.time())
    chk = lambda: pid in _cancel
    video = p["path"]
    if not video or not Path(video).exists():
        stage(pid, "downloading"); video = dl.download(p["url"], pid, p["quality"], lambda d, t: db.update("projects", pid, done=d, total=t))
        db.update("projects", pid, path=video)
    duration = dl.duration(video); db.update("projects", pid, duration=duration)
    audio = sig.has_audio(video)
    if audio:
        stage(pid, "extracting_audio"); stage(pid, "transcribing")
        tr, lang = ws.transcribe(video, work, cfg.get("whisper_model", "small"), cfg.get("device", "auto"),
                                 lambda d, t: db.update("projects", pid, done=d, total=t), chk)
    else:                                            # no audio stream at all: skip Whisper entirely
        tr, lang = Transcript([]), "none"; ws.save(tr, lang, work / "transcript")
    existing = db.all_("SELECT id,status FROM clips WHERE project_id=? AND deleted=0", (pid,))
    if existing:                                     # resume: analysis already done, only render what is unfinished
        ids = [c["id"] for c in existing if c["status"] != "ready"]
    elif (not audio) or sig.is_speechless(tr, duration):
        ids = _plan_visual(pid, video, work, duration, audio)
    else:
        ids = _analyze_speech(pid, p, video, work, tr, lang, chk)
    stage(pid, "rendering", 0, len(ids))
    for n, cid in enumerate(ids, 1):
        if chk(): raise RuntimeError("cancelled")
        render(cid, tr); db.update("projects", pid, done=n, total=len(ids))
    db.update("projects", pid, status="completed", stage="completed", finished=time.time())

def render(cid, tr=None):
    c = db.one("SELECT * FROM clips WHERE id=?", (cid,)); p = db.one("SELECT * FROM projects WHERE id=?", (c["project_id"],))
    work = PROCESSED / str(p["id"])
    if tr is None and (work / "transcript.json").exists(): tr = ws.load(work / "transcript")[0]
    words = [w for s in tr.segments for w in s.words] if tr else []
    out = work / f"clip_{cid}_{c['aspect'].replace(':','x')}.mp4"
    db.update("clips", cid, status="rendering")
    try:
        use_gpu = db.get_settings().get("device", "auto") != "cpu"
        render_clip(p["path"], c["start"], c["end"], out, words, c["aspect"], c["caption_template"], True, use_gpu)
        thumbnails(p["path"], c["start"], c["end"], work, cid, 4)
        db.update("clips", cid, out_path=str(out), status="ready")
    except Exception as e:
        db.update("clips", cid, status="failed"); raise

def _loop():
    while True:
        pid = _q.get()
        try: run_project(pid)
        except Exception as e:
            msg = str(e); st = "cancelled" if msg == "cancelled" else "failed"
            db.update("projects", pid, status=st, error=None if st == "cancelled" else msg[:900])
            if st == "failed": traceback.print_exc()
        finally: _cancel.discard(pid)

def start():
    threading.Thread(target=_loop, daemon=True).start()
    for r in db.all_("SELECT id FROM projects WHERE status IN ('queued','running')"): _q.put(r["id"])   # resume after restart
