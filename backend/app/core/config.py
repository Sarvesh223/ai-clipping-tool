"""Central, env-configurable settings. No external APIs: LLM is a local Ollama server."""
import os
from dataclasses import dataclass, field

def _f(name, default): return float(os.getenv(name, default))
def _i(name, default): return int(os.getenv(name, default))

DEFAULT_WEIGHTS = {"hook": 0.12, "information": 0.13, "emotion": 0.12, "curiosity": 0.12, "completeness": 0.12,
                   "shareability": 0.09, "retention": 0.07, "viral": 0.08, "engagement": 0.10, "independence": 0.05}

@dataclass
class Settings:
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    speed_mode: str = os.getenv("SPEED_MODE", "fast")          # fast = heuristics + short LLM rerank; quality = full LLM scan
    auto_render_top: int = _i("AUTO_RENDER_TOP", 5)            # render only the best N clips up front (0 = all)
    render_height: int = _i("RENDER_HEIGHT", 720)              # 720 renders ~2x faster than 1080
    chunk_seconds: float = _f("CHUNK_SECONDS", 180)
    chunk_overlap: float = _f("CHUNK_OVERLAP", 30)
    max_candidates_per_chunk: int = _i("MAX_CANDIDATES_PER_CHUNK", 3)
    min_clip_s: float = _f("MIN_CLIP_S", 15)
    max_clip_s: float = _f("MAX_CLIP_S", 90)
    snap_tolerance_s: float = _f("SNAP_TOLERANCE_S", 4)
    dup_similarity: float = _f("DUP_SIMILARITY", 0.72)
    weights: dict = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

settings = Settings()
