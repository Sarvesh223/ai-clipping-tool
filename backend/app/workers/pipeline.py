"""Persistent, resumable pipeline. Stages write real progress (done/total) or null when unknown."""
import json, threading, time, queue, traceback
from pathlib import Path
from ..database import db
from ..core.config import settings
from ..core.paths import PROCESSED
from ..services.downloader import ytdlp_service as dl
from ..services.transcription import whisper_service as ws
from ..services.content_analysis.analyzer import analyze
from ..services.content_analysis import llm_client
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
    if "weights" in s: settings.weights = s["weights"]
    return s

def stage(pid, name, done=None, total=None): db.update("projects", pid, stage=name, done=done, total=total, status="running")
def enqueue(pid): db.update("projects", pid, status="queued", error=None); _q.put(pid)
def cancel(pid): _cancel.add(pid)

def run_project(pid):
    p = db.one("SELECT * FROM projects WHERE id=?", (pid,)); cfg = apply_settings()
    work = PROCESSED / str(pid); work.mkdir(exist_ok=True)
    db.update("projects", pid, started=time.time())
    chk = lambda: pid in _cancel
    video = p["path"]
    if not video or not Path(video).exists():
        stage(pid, "downloading"); video = dl.download(p["url"], pid, p["quality"], lambda d, t: db.update("projects", pid, done=d, total=t))
        db.update("projects", pid, path=video)
    db.update("projects", pid, duration=dl.duration(video))
    stage(pid, "extracting_audio")
    stage(pid, "transcribing")
    tr, lang = ws.transcribe(video, work, cfg.get("whisper_model", "small"), cfg.get("device", "auto"),
                             lambda d, t: db.update("projects", pid, done=d, total=t), chk)
    existing = db.all_("SELECT id,status FROM clips WHERE project_id=? AND deleted=0", (pid,))
    if existing:                                    # resume: analysis already done, only render what is unfinished
        ids = [c["id"] for c in existing if c["status"] != "ready"]
    else:
        stage(pid, "understanding")                 # Whisper is freed; now the LLM gets the VRAM
        llm_client.check_ollama(settings.ollama_url, settings.ollama_model)
        funnel = {}
        cands = analyze(tr, p["audience"], p["style"], workers=1, stats=funnel, progress=lambda d, t: db.update("projects", pid, done=d, total=t))
        if chk(): raise RuntimeError("cancelled")
        stage(pid, "ranking")
        ranked = rank(tr, cands)
        picked, method = select_diverse(tr, ranked, target_count(tr.duration), settings.dup_similarity)
        final = optimize_all(tr, picked)
        funnel.update(ranked=len(ranked), dropped_as_duplicates=len(ranked) - len(picked), final=len(final), video_s=round(tr.duration))
        db.set_setting(f"funnel_{pid}", funnel); print("[pipeline] funnel:", funnel)
        ids = []
        for c in final:
            data = dict(hook=c.hook, main_message=c.main_message, why=c.why, audience=c.audience, titles=c.titles,
                        caption=c.caption, edit_style=c.edit_style, category=c.category, breakdown=c.score_breakdown,
                        penalties=c.penalties, language=lang, dedup=method)
            ids.append(db.run("INSERT INTO clips(project_id,start,end,score,title,data) VALUES(?,?,?,?,?,?)",
                              (pid, c.start, c.end, c.score, c.title, json.dumps(data))))
    stage(pid, "rendering", 0, len(ids))
    for n, cid in enumerate(ids, 1):
        if chk(): raise RuntimeError("cancelled")
        render(cid, tr); db.update("projects", pid, done=n, total=len(ids))
    db.update("projects", pid, status="completed", stage="completed", finished=time.time())

def render(cid, tr=None):
    c = db.one("SELECT * FROM clips WHERE id=?", (cid,)); p = db.one("SELECT * FROM projects WHERE id=?", (c["project_id"],))
    work = PROCESSED / str(p["id"])
    tr = tr or ws.load(work / "transcript")[0]
    words = [w for s in tr.segments for w in s.words]
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
