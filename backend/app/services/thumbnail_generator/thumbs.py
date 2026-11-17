import subprocess
def thumbnails(video, start, end, outdir, cid, n=4):
    outs = []
    for i in range(n):
        t = start + (end - start) * (i + 1) / (n + 1); p = outdir / f"thumb_{cid}_{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-q:v", "3", str(p)], capture_output=True)
        if p.exists(): outs.append(p.name)
    return outs
