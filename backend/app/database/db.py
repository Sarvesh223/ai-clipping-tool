import sqlite3, threading, json, time
from ..core.paths import DBDIR
_lock = threading.RLock()
_conn = sqlite3.connect(DBDIR / "app.db", check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.executescript("""
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, title TEXT, url TEXT, path TEXT, thumb TEXT,
  duration REAL, status TEXT DEFAULT 'queued', stage TEXT, done INTEGER, total INTEGER, error TEXT,
  audience TEXT DEFAULT 'General audience', style TEXT DEFAULT 'Educational', quality INTEGER DEFAULT 720,
  created REAL, started REAL, finished REAL);
CREATE TABLE IF NOT EXISTS clips(id INTEGER PRIMARY KEY, project_id INTEGER, start REAL, end REAL, score REAL,
  title TEXT, data TEXT, aspect TEXT DEFAULT '9:16', caption_template TEXT DEFAULT 'bold_yellow',
  out_path TEXT, status TEXT DEFAULT 'pending', deleted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS exports(id INTEGER PRIMARY KEY, clip_id INTEGER, path TEXT, created REAL);
""")
def run(sql, args=()):
    with _lock:
        cur = _conn.execute(sql, args); _conn.commit(); return cur.lastrowid
def all_(sql, args=()):
    with _lock: return [dict(r) for r in _conn.execute(sql, args).fetchall()]
def one(sql, args=()):
    r = all_(sql, args); return r[0] if r else None
def update(table, id_, **kw):
    run(f"UPDATE {table} SET " + ",".join(f"{k}=?" for k in kw) + " WHERE id=?", (*kw.values(), id_))
def get_settings():
    return {r["key"]: json.loads(r["value"]) for r in all_("SELECT * FROM settings")}
def set_setting(k, v): run("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, json.dumps(v)))
