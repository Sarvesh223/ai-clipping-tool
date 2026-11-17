"""Central, env-configurable settings. No external APIs: LLM is a local Ollama server."""
import os
from dataclasses import dataclass, field

def _f(name, default): return float(os.getenv(name, default))
def _i(name, default): return int(os.getenv(name, default))

@dataclass
class Settings:
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    chunk_seconds: float = _f("CHUNK_SECONDS", 180)
    chunk_overlap: float = _f("CHUNK_OVERLAP", 30)
    max_candidates_per_chunk: int = _i("MAX_CANDIDATES_PER_CHUNK", 3)
    min_clip_s: float = _f("MIN_CLIP_S", 15)
    max_clip_s: float = _f("MAX_CLIP_S", 90)
    snap_tolerance_s: float = _f("SNAP_TOLERANCE_S", 4)
    dup_similarity: float = _f("DUP_SIMILARITY", 0.72)
    weights: dict = field(default_factory=lambda: {
        "hook": 0.20, "information": 0.20, "emotion": 0.15, "curiosity": 0.15,
        "completeness": 0.15, "engagement": 0.10, "independence": 0.05})

settings = Settings()
