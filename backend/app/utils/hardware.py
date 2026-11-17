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
    return info
