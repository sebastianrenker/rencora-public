"""
Rencora Brain — a per-user index of files, code and prompts as searchable "neurons".

Two sources, shown in two colours in the /brain HUD:
  - rencora  (purple) : Rencora's own code/config
  - claude   (orange) : the user's Claude Code data (sessions/prompts/memory)

Stored in a local SQLite DB (config/brain.db) with full-text search, so Rencora can
know everything in these files and help with coding. Roots are configurable per user
in config/brain.json -> {"roots":[{"path":"...","source":"rencora|claude|user"}]}.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
import os
import sqlite3
import time
from pathlib import Path
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "config" / "brain.db"
CFG_PATH = BASE / "config" / "brain.json"

TEXT_EXT = {"py", "js", "ts", "jsx", "tsx", "html", "css", "md", "txt", "json", "jsonl",
            "yaml", "yml", "csv", "sh", "bat", "vbs", "xml", "ini", "cfg", "toml", "prompt", "env"}
SKIP_DIR = {"node_modules", ".git", "__pycache__", "venv", ".venv", "env", "dist", "build",
            "site-packages", ".cache", "uploads", "models", "build_exe", "dist_exe",
            "appdata", "windows", "program files", "program files (x86)", "programdata",
            "$recycle.bin", "temp", "tmp", "cache", "caches", "logs", ".gradle", ".nuget",
            ".vscode", "obj", "bin", ".next", ".pytest_cache", "vendor"}
MAX_FILE = 120_000          # bytes of text stored per file
MAX_FILES = 300_000         # very large — index essentially all text/code/doc files


DOC_EXT = {"pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "odt", "ods", "rtf", "epub"}


def _cfg():
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _index_all():
    return bool(_cfg().get("index_all_files", False))


def _default_roots():
    home = Path.home()
    roots = [{"path": str(BASE), "source": "rencora"}]
    claude = home / ".claude" / "projects"
    if claude.exists():
        roots.append({"path": str(claude), "source": "claude"})
    # PC files: the user's own documents/code across their main folders (text/doc only, filtered)
    for sub in ("Documents", "Desktop", "Downloads", "OneDrive", "source", "Projects", "code"):
        d = home / sub
        if d.exists():
            roots.append({"path": str(d), "source": "pc"})
    return roots


def _roots():
    cfg = _cfg()
    r = cfg.get("roots")
    return r if r else _default_roots()


def _github_username():
    # owner.json is the source of truth
    for fname, key in (("owner.json", "github"), ("github.json", "username")):
        try:
            u = json.loads((BASE / "config" / fname).read_text(encoding="utf-8")).get(key, "")
            if u:
                return u.strip()
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return ""


def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.execute("""CREATE TABLE IF NOT EXISTS nodes(
        id INTEGER PRIMARY KEY, path TEXT UNIQUE, name TEXT, source TEXT,
        ext TEXT, folder TEXT, size INTEGER, mtime REAL)""")
    con.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS content
        USING fts5(text, path UNINDEXED, name UNINDEXED, source UNINDEXED)""")
    return con


def scan(incremental=False, do_github=True):
    """Build/refresh the index. incremental=True only re-reads changed local files
    (fast, gentle for the background auto-scan); do_github toggles the GitHub refresh."""
    con = _db()
    LOCAL_SRC = {"rencora", "claude", "pc", "user"}
    existing = {}
    if incremental:
        for path, mtime, source in con.execute("SELECT path,mtime,source FROM nodes"):
            if source in LOCAL_SRC:
                existing[path] = mtime
    else:
        con.execute("DELETE FROM nodes")
        con.execute("DELETE FROM content")
    counts = {}
    n = 0
    seen = set()
    for root in _roots():
        base = Path(root.get("path", ""))
        src = root.get("source", "user")
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIR]
            for fn in filenames:
                ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                is_text = ext in TEXT_EXT
                is_doc = ext in DOC_EXT
                # Default: meaningful files — code/text (with content) + real documents
                # (pdf/docx/xls…, as neurons). index_all_files=true also grabs every other file.
                if not is_text and not is_doc and not (src == "pc" and _index_all()):
                    continue
                p = Path(dirpath) / fn
                path = str(p)
                try:
                    stt = p.stat(); size = stt.st_size; mtime = stt.st_mtime
                except Exception:
                    continue
                seen.add(path)
                if incremental and path in existing and abs(existing[path] - mtime) < 1:
                    continue                       # unchanged -> skip (fast)
                if is_text and size <= 3_000_000:
                    try:
                        text = p.read_text(encoding="utf-8", errors="replace")[:MAX_FILE]
                    except Exception:
                        text = fn
                else:
                    text = fn                      # non-text: searchable by name/path only
                folder = str(p.parent)
                try:
                    if incremental:
                        con.execute("DELETE FROM nodes WHERE path=?", (path,))
                        con.execute("DELETE FROM content WHERE path=?", (path,))
                    con.execute(
                        "INSERT OR IGNORE INTO nodes(path,name,source,ext,folder,size,mtime) VALUES(?,?,?,?,?,?,?)",
                        (path, fn, src, ext, folder, size, mtime))
                    con.execute("INSERT INTO content(text,path,name,source) VALUES(?,?,?,?)",
                                (text, path, fn, src))
                    counts[src] = counts.get(src, 0) + 1
                    n += 1
                except Exception:
                    continue
                if n >= MAX_FILES:
                    break
            if n >= MAX_FILES:
                break
        if n >= MAX_FILES:
            break
    if incremental:                              # drop local files that no longer exist
        for path in existing:
            if path not in seen:
                con.execute("DELETE FROM nodes WHERE path=?", (path,))
                con.execute("DELETE FROM content WHERE path=?", (path,))
    if do_github:                                # GitHub: repo files + recent commits (changes)
        try:
            if incremental:
                con.execute("DELETE FROM nodes WHERE source='github'")
                con.execute("DELETE FROM content WHERE source='github'")
            gc = _scan_github(con)
            if gc:
                counts["github"] = gc
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    con.commit()
    con.close()
    return counts


_auto_started = False
def start_auto(local_interval=600, github_interval=3300):
    """Background auto-scan: incremental local re-index every ~10 min, GitHub ~hourly.
    Runs a full scan first if the index is empty. Safe to call once at startup."""
    global _auto_started
    if _auto_started:
        return
    _auto_started = True
    import threading
    import time as _t

    def _loop():
        try:
            if stats().get("total", 0) == 0:
                scan(incremental=False, do_github=True)
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
        last_gh = _t.time()
        while True:
            _t.sleep(local_interval)
            try:
                do_gh = (_t.time() - last_gh) >= github_interval
                scan(incremental=True, do_github=do_gh)
                if do_gh:
                    last_gh = _t.time()
            except Exception:
                _swallow_log.debug("ignored error", exc_info=True)

    threading.Thread(target=_loop, daemon=True).start()


def _gh(url):
    try:
        import requests
        r = requests.get(url, headers={"Accept": "application/vnd.github+json",
                                       "User-Agent": "Rencora"}, timeout=15)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _scan_github(con):
    """Index every repo's file tree + its recent commits (changes)."""
    user = _github_username()
    if not user:
        return 0
    repos = _gh("https://api.github.com/users/%s/repos?per_page=100&sort=updated" % user)
    if not repos:
        return 0
    added = 0
    for repo in repos[:25]:
        if repo.get("fork"):
            continue
        name = repo.get("name", "")
        branch = repo.get("default_branch", "main")
        folder = "github/" + name
        tree = _gh("https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1" % (user, name, branch))
        if tree and isinstance(tree.get("tree"), list):
            for e in tree["tree"][:400]:
                if e.get("type") != "blob":
                    continue
                fn = e.get("path", "").rsplit("/", 1)[-1]
                ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                path = "gh:" + name + "/" + e.get("path", "")
                try:
                    cur = con.execute(
                        "INSERT OR IGNORE INTO nodes(path,name,source,ext,folder,size,mtime) VALUES(?,?,?,?,?,?,?)",
                        (path, fn, "github", ext, folder, e.get("size", 0), 0))
                    if cur.rowcount:
                        con.execute("INSERT INTO content(text,path,name,source) VALUES(?,?,?,?)",
                                    (name + "/" + e.get("path", ""), path, fn, "github"))
                        added += 1
                except Exception:
                    _swallow_log.debug("ignored error", exc_info=True)
        commits = _gh("https://api.github.com/repos/%s/%s/commits?per_page=30" % (user, name))
        if commits and isinstance(commits, list):
            for c in commits:
                cm = (c.get("commit") or {})
                msg = (cm.get("message") or "").strip()
                date = ((cm.get("author") or {}).get("date") or "")[:10]
                sha = (c.get("sha") or "")[:7]
                if not msg:
                    continue
                short = (msg.splitlines()[0])[:70]
                path = "ghc:" + name + "/" + sha
                try:
                    cur = con.execute(
                        "INSERT OR IGNORE INTO nodes(path,name,source,ext,folder,size,mtime) VALUES(?,?,?,?,?,?,?)",
                        (path, "⟳ " + short, "github", "commit", folder, 0, 0))
                    if cur.rowcount:
                        con.execute("INSERT INTO content(text,path,name,source) VALUES(?,?,?,?)",
                                    ("[" + name + " " + date + "] " + msg, path, short, "github"))
                        added += 1
                except Exception:
                    _swallow_log.debug("ignored error", exc_info=True)
    return added


def search(query, limit=8):
    con = _db()
    out = []
    try:
        import re as _re
        toks = [t for t in _re.split(r"\s+", query.strip()) if len(t) >= 3][:6]
        q = " OR ".join('"' + t.replace('"', '') + '"*' for t in toks) if toks else query
        rows = con.execute(
            "SELECT name, path, source, snippet(content,0,'[',']','…',12) "
            "FROM content WHERE content MATCH ? LIMIT ?", (q, limit)).fetchall()
        for name, path, source, snip in rows:
            out.append({"name": name, "path": path, "source": source, "snippet": snip})
    except Exception:
        # fallback LIKE
        try:
            rows = con.execute(
                "SELECT name, path, source, substr(text,1,200) FROM content WHERE text LIKE ? LIMIT ?",
                ("%" + query + "%", limit)).fetchall()
            for name, path, source, snip in rows:
                out.append({"name": name, "path": path, "source": source, "snippet": snip})
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    con.close()
    return out


def graph(limit=2500):
    con = _db()
    total = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    srcs = [r[0] for r in con.execute("SELECT DISTINCT source FROM nodes").fetchall()]
    per = max(80, limit // max(1, len(srcs)))
    rows = []
    for s in srcs:                       # balanced sample so EVERY brain/source shows
        rows += con.execute(
            "SELECT id,name,source,ext,folder,size,mtime FROM nodes WHERE source=? "
            "ORDER BY mtime DESC, id DESC LIMIT ?", (s, per)).fetchall()
    con.close()
    nodes, byfolder = [], {}
    for i, (nid, name, source, ext, folder, size, mtime) in enumerate(rows):
        nodes.append({"id": nid, "name": name, "source": source, "ext": ext, "size": size})
        byfolder.setdefault((source, folder), []).append(nid)
    edges = []
    for (_src, _folder), ids in byfolder.items():
        hub = ids[0]                     # star per folder = sparse clusters
        for other in ids[1:]:
            edges.append([hub, other])
    return {"nodes": nodes, "edges": edges, "total": total, "shown": len(nodes)}


def node(node_id):
    con = _db()
    row = con.execute("SELECT path,name,source FROM nodes WHERE id=?", (node_id,)).fetchone()
    text = ""
    if row:
        try:
            r2 = con.execute("SELECT text FROM content WHERE path=? LIMIT 1", (row[0],)).fetchone()
            text = r2[0] if r2 else ""
        except Exception:
            text = ""
    con.close()
    if not row:
        return None
    return {"path": row[0], "name": row[1], "source": row[2], "text": text[:60000]}


def stats():
    con = _db()
    try:
        total = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        bysrc = dict(con.execute("SELECT source,COUNT(*) FROM nodes GROUP BY source").fetchall())
    except Exception:
        total, bysrc = 0, {}
    con.close()
    return {"total": total, "by_source": bysrc}
