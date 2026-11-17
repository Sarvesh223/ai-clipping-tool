from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
DOWNLOADS, PROCESSED, EXPORTS, DBDIR = (ROOT / d for d in ("downloads", "processed", "exports", "database"))
for p in (DOWNLOADS, PROCESSED, EXPORTS, DBDIR): p.mkdir(exist_ok=True)
