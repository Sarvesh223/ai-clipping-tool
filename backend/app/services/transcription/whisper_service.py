import json, subprocess, gc
from pathlib import Path
from ..content_analysis.models import Transcript, Segment, Word

def extract_audio(video, wav):
    subprocess.run(["ffmpeg", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav],
                   check=True, capture_output=True)

def load_wav(path):
    """Read the 16 kHz mono PCM WAV that ffmpeg made -> float32 array. Bypasses PyAV (version-mismatch proof)."""
    import wave, numpy as np
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

def _srt_time(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")

def save(tr: Transcript, lang, base: Path):
    data = {"language": lang, "segments": [{"start": s.start, "end": s.end, "text": s.text,
            "words": [w.__dict__ for w in s.words]} for s in tr.segments]}
    base.with_suffix(".json").write_text(json.dumps(data), encoding="utf-8")
    base.with_suffix(".srt").write_text("\n".join(f"{i}\n{_srt_time(s.start)} --> {_srt_time(s.end)}\n{s.text.strip()}\n"
        for i, s in enumerate(tr.segments, 1)), encoding="utf-8")

def load(base: Path):
    d = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    return Transcript([Segment(s["start"], s["end"], s["text"], [Word(**w) for w in s["words"]]) for s in d["segments"]]), d["language"]

def _add_cuda_dlls():
    """Make pip-installed NVIDIA DLLs (cublas/cudnn) loadable on Windows, regardless of PATH."""
    import os, sys, glob
    for base in sys.path:
        for d in glob.glob(os.path.join(base, "nvidia", "*", "bin")):
            try: os.add_dll_directory(d)
            except (AttributeError, OSError): pass
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

def _run(m, audio, model, on_progress, cancelled):
    segs_iter, info = m.transcribe(audio, word_timestamps=True, vad_filter=True, beam_size=1 if model in ("tiny", "base") else 3)
    segs = []
    for s in segs_iter:
        if cancelled(): raise RuntimeError("cancelled")
        segs.append(Segment(s.start, s.end, s.text, [Word(w.start, w.end, w.word) for w in (s.words or [])]))
        if on_progress and info.duration: on_progress(int(s.end), int(info.duration))   # real: audio seconds done / total
    return segs, info

def transcribe(video, workdir: Path, model="small", device="auto", on_progress=None, cancelled=lambda: False):
    """Cached/resumable. Tries GPU; on ANY CUDA failure (even mid-run) transparently redoes it on CPU."""
    base = workdir / "transcript"
    if base.with_suffix(".json").exists(): return load(base)
    wav = workdir / "audio.wav"
    if not wav.exists(): extract_audio(video, str(wav))
    audio = load_wav(wav)
    _add_cuda_dlls()
    from faster_whisper import WhisperModel
    import ctranslate2
    want_cuda = device == "cuda" or (device == "auto" and ctranslate2.get_cuda_device_count() > 0)
    result = None
    if want_cuda:
        try:
            m = WhisperModel(model, device="cuda", compute_type="int8_float16")
            result = _run(m, audio, model, on_progress, cancelled); del m
        except Exception as e:
            if str(e) == "cancelled": raise
            print(f"[whisper] GPU failed ({e}); falling back to CPU. Fix: Settings -> Device -> CPU, or install CUDA libs.")
            gc.collect()
    if result is None:
        m = WhisperModel(model, device="cpu", compute_type="int8")
        result = _run(m, audio, model, on_progress, cancelled); del m
    segs, info = result
    tr = Transcript(segs); save(tr, info.language, base)
    gc.collect()
    return tr, info.language
