import shutil, subprocess
def hardware():
    info = {"ffmpeg": bool(shutil.which("ffmpeg")), "ollama": bool(shutil.which("ollama")),
            "cuda": False, "gpu": None, "vram_mb": None}
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout.strip().split(",")
        info["gpu"], info["vram_mb"] = out[0].strip(), int(out[1])
    except Exception: pass
    try:
        import ctranslate2; info["cuda"] = ctranslate2.get_cuda_device_count() > 0
    except Exception: pass
    info["ram_gb"] = ram_gb()
    return info

def ram_gb():
    try:
        import ctypes
        class M(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                        ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
        m = M(); m.l = ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); return round(m.tp / 2**30, 1)
    except Exception:
        try: return round(int(open("/proc/meminfo").read().split()[1]) / 2**20, 1)
        except Exception: return None

def recommend(h):
    """Pick settings that keep a small laptop fast."""
    vram, ram = h.get("vram_mb") or 0, h.get("ram_gb") or 8
    if not h.get("cuda") or vram < 3000 or ram < 8:
        return dict(whisper_model="base", ollama_model="qwen3:1.7b", device="cpu", speed_mode="fast", render_height=720, auto_render_top=3)
    if vram < 6000:
        return dict(whisper_model="base", ollama_model="qwen3:4b", device="auto", speed_mode="fast", render_height=720, auto_render_top=5)
    return dict(whisper_model="small", ollama_model="qwen3:8b", device="auto", speed_mode="fast", render_height=1080, auto_render_top=8)
