import json, shutil, tempfile, threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .core.paths import PROCESSED, EXPORTS, DOWNLOADS
from .database import db
from .workers import pipeline
from .utils.hardware import hardware, recommend
from .services.downloader import ytdlp_service as dl
from .services.caption_generator.ass import TEMPLATES
from .services.content_analysis import llm_client
from .core.config import settings

app = FastAPI(title="Local Clip Studio")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def _s(): pipeline.start()

# Recommended presets for GTX 1650 Ti (4 GB VRAM) / 16 GB RAM
PRESETS = {"fastest": dict(whisper_model="base", ollama_model="qwen3:1.7b", device="auto", speed_mode="fast", render_height=720, auto_render_top=3),
           "fast": dict(whisper_model="base", ollama_model="qwen3:4b", device="auto", speed_mode="fast", render_height=720, auto_render_top=5),
           "quality": dict(whisper_model="small", ollama_model="qwen3:4b", device="auto", speed_mode="quality", render_height=1080, auto_render_top=0)}

class NewProject(BaseModel):
    url: str; quality: int = 720; audience: str = "General audience"; style: str = "Educational"

@app.get("/api/health")
def health():
    h = hardware(); out = dict(hardware=h, presets=PRESETS, recommended=recommend(h), templates=list(TEMPLATES))
    try: out["ollama"] = llm_client.check_ollama(settings.ollama_url, settings.ollama_model)
    except Exception as e: out["ollama"] = {"ok": False, "error": str(e)}
    return out

@app.get("/api/settings")
def get_settings(): return {**PRESETS["fast"], **db.get_settings()}
@app.put("/api/settings")
def put_settings(body: dict):
    for k, v in body.items(): db.set_setting(k, v)
    return get_settings()

@app.post("/api/projects")
def create(b: NewProject):
    try: info = dl.probe(b.url)
    except Exception as e: raise HTTPException(400, f"Cannot read URL: {e}")
    pid = db.run("INSERT INTO projects(title,url,thumb,duration,audience,style,quality,created) VALUES(?,?,?,?,?,?,?,?)",
                 (info["title"], b.url, info["thumb"], info["duration"], b.audience, b.style, b.quality, __import__("time").time()))
    pipeline.enqueue(pid); return db.one("SELECT * FROM projects WHERE id=?", (pid,))

@app.post("/api/projects/upload")
async def upload(file: UploadFile = File(...), audience: str = Form("General audience"), style: str = Form("Educational")):
    if Path(file.filename).suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm"): raise HTTPException(400, "Unsupported file type")
    pid = db.run("INSERT INTO projects(title,audience,style,created) VALUES(?,?,?,?)", (file.filename, audience, style, __import__("time").time()))
    dst = DOWNLOADS / f"{pid}{Path(file.filename).suffix.lower()}"
    with open(dst, "wb") as f: shutil.copyfileobj(file.file, f)
    db.update("projects", pid, path=str(dst)); pipeline.enqueue(pid); return db.one("SELECT * FROM projects WHERE id=?", (pid,))

@app.get("/api/projects")
def projects():
    return db.all_("SELECT p.*, (SELECT COUNT(*) FROM clips c WHERE c.project_id=p.id AND c.deleted=0) AS clip_count, "
                   "(SELECT MAX(score) FROM clips c WHERE c.project_id=p.id AND c.deleted=0) AS best FROM projects p ORDER BY id DESC")
@app.get("/api/projects/{pid}")
def project(pid: int):
    p = db.one("SELECT * FROM projects WHERE id=?", (pid,))
    if not p: raise HTTPException(404)
    clips = db.all_("SELECT * FROM clips WHERE project_id=? AND deleted=0 ORDER BY score DESC", (pid,))
    for c in clips: c["data"] = json.loads(c["data"] or "{}")
    p["funnel"] = db.get_settings().get(f"funnel_{pid}")
    scores = [c["score"] for c in clips]
    p["stats"] = dict(clips=len(clips), avg_score=round(sum(scores)/len(scores), 1) if scores else None, best=max(scores) if scores else None,
                      processing_s=round((p["finished"] or __import__("time").time()) - p["started"], 1) if p["started"] else None)
    return {**p, "clips_list": clips}
@app.post("/api/projects/{pid}/cancel")
def cancel(pid: int): pipeline.cancel(pid); return {"ok": True}
@app.post("/api/projects/{pid}/retry")
def retry(pid: int, reanalyze: bool = False):
    if reanalyze: db.run("DELETE FROM clips WHERE project_id=?", (pid,))   # default keeps found clips, renders only unfinished
    pipeline.enqueue(pid); return {"ok": True}
@app.delete("/api/projects/{pid}")
def delete_project(pid: int):
    db.run("DELETE FROM clips WHERE project_id=?", (pid,)); db.run("DELETE FROM projects WHERE id=?", (pid,))
    shutil.rmtree(PROCESSED / str(pid), ignore_errors=True); return {"ok": True}
@app.get("/api/projects/{pid}/transcript")
def transcript(pid: int): return json.loads((PROCESSED / str(pid) / "transcript.json").read_text(encoding="utf-8"))

class ClipEdit(BaseModel):
    start: float | None = None; end: float | None = None; aspect: str | None = None
    caption_template: str | None = None; title: str | None = None
@app.patch("/api/clips/{cid}")
def edit_clip(cid: int, b: ClipEdit):
    kw = {k: v for k, v in b.model_dump().items() if v is not None}
    if "aspect" in kw and kw["aspect"] not in ("9:16", "16:9", "1:1"): raise HTTPException(400, "bad aspect")
    if kw: db.update("clips", cid, **kw)
    return db.one("SELECT * FROM clips WHERE id=?", (cid,))
@app.post("/api/clips/{cid}/render")
def rerender(cid: int):
    threading.Thread(target=lambda: pipeline.render(cid), daemon=True).start(); return {"ok": True}
@app.delete("/api/clips/{cid}")
def del_clip(cid: int): db.update("clips", cid, deleted=1); return {"ok": True}
@app.get("/api/clips/{cid}/video")
def clip_video(cid: int):
    c = db.one("SELECT * FROM clips WHERE id=?", (cid,))
    if not c or not c["out_path"]: raise HTTPException(404)
    return FileResponse(c["out_path"], media_type="video/mp4", headers={"Cache-Control": "no-cache"})
@app.get("/api/clips/{cid}/thumb/{i}")
def clip_thumb(cid: int, i: int):
    c = db.one("SELECT * FROM clips WHERE id=?", (cid,)); return FileResponse(PROCESSED / str(c["project_id"]) / f"thumb_{cid}_{i}.jpg")
@app.post("/api/clips/{cid}/export")
def export(cid: int):
    c = db.one("SELECT * FROM clips WHERE id=?", (cid,))
    if not c or not c["out_path"]: raise HTTPException(400, "Render first")
    safe = "".join(ch for ch in (c["title"] or "clip") if ch.isalnum() or ch in " -_")[:50].strip() or "clip"
    dst = EXPORTS / f"{cid}_{safe}.mp4"; shutil.copy(c["out_path"], dst)
    db.run("INSERT INTO exports(clip_id,path,created) VALUES(?,?,?)", (cid, str(dst), __import__("time").time())); return {"path": str(dst)}
@app.get("/api/exports")
def exports(): return db.all_("SELECT * FROM exports ORDER BY id DESC")
