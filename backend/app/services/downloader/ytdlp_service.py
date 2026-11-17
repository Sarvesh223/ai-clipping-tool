"""Downloads only what yt-dlp can legitimately fetch; no DRM/access-control circumvention."""
import shutil, subprocess, json
from pathlib import Path
from ...core.paths import DOWNLOADS

def probe(url):
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "noplaylist": True}) as y:
        i = y.extract_info(url, download=False)
    return {"title": i.get("title"), "duration": i.get("duration"), "thumb": i.get("thumbnail"), "id": i.get("id")}

def download(url, pid, quality=720, on_progress=None):
    import yt_dlp
    def hook(d):
        if d["status"] == "downloading" and on_progress:
            on_progress(d.get("downloaded_bytes", 0), d.get("total_bytes") or d.get("total_bytes_estimate"))
    opts = {"format": f"bv*[height<={quality}]+ba/b[height<={quality}]", "merge_output_format": "mp4",
            "outtmpl": str(DOWNLOADS / f"{pid}.%(ext)s"), "noplaylist": True, "quiet": True,
            "progress_hooks": [hook], "continuedl": True}
    with yt_dlp.YoutubeDL(opts) as y: y.download([url])
    return str(DOWNLOADS / f"{pid}.mp4")

def import_local(src, pid):
    dst = DOWNLOADS / f"{pid}{Path(src).suffix.lower()}"
    shutil.copy(src, dst)
    return str(dst)

def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    return float(json.loads(r.stdout)["format"]["duration"])
