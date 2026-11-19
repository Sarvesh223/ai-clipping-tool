import subprocess, shutil, json
from pathlib import Path
from . import framing
from ..caption_generator.ass import build_ass

SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}

def _probe(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "json", video], capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]; return s["width"], s["height"]

def nvenc_ok():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return "h264_nvenc" in r.stdout

def render_clip(video, start, end, out, words=None, aspect="9:16", template="bold_yellow", captions=True, use_gpu=False, height=1080):
    out = Path(out); work = out.parent / f".w_{out.stem}"; work.mkdir(parents=True, exist_ok=True)
    W, H = SIZES[aspect]; k = height / 1080; W, H = int(W * k) // 2 * 2, int(H * k) // 2 * 2; sw, sh = _probe(video); dur = end - start
    mode = "scale"
    f = ""
    if aspect != "16:9" or abs(sw / sh - W / H) > 0.05:
        crop_w = min(sw, int(sh * W / H) // 2 * 2)
        if crop_w < sw:                                   # source is wider than target: try face-tracked crop
            try:
                pts, _ = framing.sample_faces(video, start, end)
                path = framing.crop_path(pts, sw, crop_w, dur)
            except Exception:                              # OpenCV missing/broken: blurred fallback, never crash
                path = None
            if path:
                mode = "track"
                f = f"[0:v]crop=w={crop_w}:h={sh}:x='{framing.x_expr(path)}':y=0,scale={W}:{H}:flags=lanczos[v0]"
        if mode == "scale":                                # blurred-background fallback
            f = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=25:5[bg];"
                 f"[b]scale={W}:-2:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v0]")
    else: f = f"[0:v]scale={W}:{H}[v0]"
    last = "v0"
    if captions and words:
        (work / "c.ass").write_text(build_ass(words, start, end, W, H, template), encoding="utf-8")
        f += f";[v0]subtitles=c.ass[v1]"; last = "v1"
    cpu = ["-c:v", "libx264", "-preset", "superfast" if height < 1080 else "veryfast", "-crf", "22"]
    gpu = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
    def build(venc): return ["ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", str(Path(video).resolve()), "-t", f"{dur:.2f}",
           "-filter_complex", f, "-map", f"[{last}]", "-map", "0:a?", *venc,
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out.resolve())]
    r = None
    if use_gpu and nvenc_ok():
        r = subprocess.run(build(gpu), cwd=work, capture_output=True, text=True)
    if r is None or r.returncode:                      # GPU encoder missing/unusable: CPU x264 always works
        r = subprocess.run(build(cpu), cwd=work, capture_output=True, text=True)
    shutil.rmtree(work, ignore_errors=True)
    if r.returncode: raise RuntimeError(r.stderr[-800:])
    return mode
