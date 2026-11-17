"""Face tracking (OpenCV Haar, no extra downloads) -> smoothed crop path -> ffmpeg x(t) expression."""
import cv2, statistics

def sample_faces(video, start, end, step=1.0):
    cap = cv2.VideoCapture(video)
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    pts, t = [], start
    W = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if ok:
            small = cv2.resize(f, None, fx=0.5, fy=0.5)
            g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = det.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
            if len(faces):
                prev = pts[-1][1] if pts and pts[-1][1] is not None else None
                # choose face nearest previous centre, else the largest (closest speaker proxy)
                key = (lambda r: abs((r[0] + r[2] / 2) * 2 - prev)) if prev is not None else (lambda r: -r[2] * r[3])
                x, y, w, h = min(faces, key=key)
                pts.append((t - start, (x + w / 2) * 2))
            else: pts.append((t - start, None))
        t += step
    cap.release()
    return pts, W

def crop_path(pts, src_w, crop_w, dur):
    """Return [(t, x_left)] smoothed (EMA) and dead-zoned, or None if tracking unreliable."""
    seen = [p for p in pts if p[1] is not None]
    if len(pts) < 2 or len(seen) < 0.5 * len(pts): return None
    out, cur = [], statistics.median(c for _, c in seen)
    for t, c in pts:
        if c is not None and abs(c - cur) > crop_w * 0.12: cur = 0.7 * cur + 0.3 * c   # dead-zone + smoothing
        x = min(max(cur - crop_w / 2, 0), src_w - crop_w)
        out.append((t, x))
    if out[-1][0] < dur: out.append((dur, out[-1][1]))
    return out

def x_expr(path):
    """Piecewise-linear x(t) for ffmpeg crop; commas are safe because the filter is read from a script file."""
    if max(x for _, x in path) - min(x for _, x in path) < 4: return f"{path[0][1]:.1f}"
    e = f"{path[-1][1]:.1f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(path, path[1:]))):
        if t1 > t0: e = f"if(lt(t,{t1:.2f}),{x0:.1f}+({x1-x0:.1f})*(t-{t0:.2f})/{t1-t0:.2f},{e})"
    return e
