# Local AI Viral Clip Intelligence (work in progress)

All AI runs locally (Ollama, faster-whisper, sentence-transformers). No API keys.


- Whisper `small` (int8 on GPU, auto CPU fallback) -> freed -> Ollama `qwen3:4b`. They never share VRAM.
- Do not use `qwen3:8b` / Whisper `medium` at the same time as other GPU apps; they may spill to CPU (slow, still works).
- Rendering uses NVENC when it works, otherwise CPU x264 (automatic).
- Expect roughly: 1 h video = ~10-20 min transcription, LLM analysis ~15-40 min on this GPU. Close games/browsers first.

## Install (Windows 10/11)
1. Install Python 3.10-3.12 (tick "Add to PATH"), Node 18+ (for the UI later), and NVIDIA driver.
2. `winget install Gyan.FFmpeg`  and install Ollama from https://ollama.com/download
3. Double-click `setup_windows.bat`, then `ollama pull qwen3:4b`
4. Double-click `start_windows.bat` — two windows open (API + UI) and the browser opens http://127.0.0.1:5173

## Implemented
Download (yt-dlp) / local import -> FFmpeg audio -> faster-whisper (word timestamps, JSON+SRT, cached/resumable)
-> chunked local-LLM analysis with timestamp/quote validation -> weighted scoring with penalties
-> semantic dedup -> word-level boundary optimisation -> FFmpeg render (9:16 / 1:1 / 16:9,
face-tracked crop with blurred fallback) -> karaoke captions (3 templates) -> thumbnails -> export.
SQLite persistence, queue resumes after restart, cancel/retry, real progress (done/total).
REST API: see /docs (projects, clips edit/re-render/delete/export, settings, health, hardware).

## Limitations and working on progress (honest)
- React UI (8 pages) is written and syntax-checked but has never been run in a browser; expect small first-run fixes.
- Not implemented: max-memory limit, parallel-worker count (kept at 1 on purpose for 4 GB VRAM), diarization, emoji captions, saved export presets, multi-video batch UI (queue works, videos run one at a time).
- Face tracking uses OpenCV Haar (frontal faces). Multi-speaker "active speaker" = nearest-to-previous face; no lip-motion/diarization yet.
- Scores estimate content quality, not virality. Visual engagement not scored.
- Only tested here with synthetic video + a stand-in LLM; the real Ollama/Whisper/yt-dlp path is untested.
