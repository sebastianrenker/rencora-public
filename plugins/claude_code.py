"""
Rencora ↔ Claude Code — Rencora delegates real coding to the Claude Code CLI, which
already has access to the owner's git repos and runs on the owner's Claude plan (not the
paid Gemini API). So Rencora can "code for you for free" using Claude + your repos, and
it takes coding load off Gemini (helps the quota/Denkaussetzer).

Runs in the background: Rencora says "Claude arbeitet dran" and announces the result via
request_say when done.

config/claude_code.json (optional):
  { "repos_dir": "C:/Users/<you>/code", "default_repo": "", "autonomy": "safe", "timeout": 300 }
  autonomy: "safe" = auto-accept file edits (--permission-mode acceptEdits);
            "full" = fully autonomous incl. running commands (--dangerously-skip-permissions).

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

_CFG = Path(__file__).resolve().parent.parent / "config" / "claude_code.json"

PLUGIN = {
    "name": "claude_code",
    "description": (
        "Delegate a REAL coding task to Claude Code in the owner's git repos (reads/writes code, "
        "fixes bugs, implements features, explains code). Runs on the owner's Claude plan (free vs "
        "the paid Gemini API) and knows their repos. Use for ANY coding/programming request: "
        "'programmier …', 'fix den Bug in …', 'bau ein Feature in Repo X', 'erklär den Code in …', "
        "'lass Claude … coden'. It runs in the background; you announce when done."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING", "description": "The full coding task / instruction for Claude"},
            "repo": {"type": "STRING", "description": "Optional repo/folder name to work in (under repos_dir)"},
        },
        "required": ["task"],
    },
}


def _cfg():
    try:
        return json.loads(_CFG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _claude():
    p = shutil.which("claude") or shutil.which("claude.cmd")
    if p:
        return p
    for c in (os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
              os.path.expandvars(r"%APPDATA%\npm\claude")):
        if os.path.exists(c):
            return c
    return None


def _resolve_dir(repo):
    cfg = _cfg()
    base = Path(cfg.get("repos_dir") or (Path.home()))
    repo = (repo or cfg.get("default_repo") or "").strip()
    if repo:
        cand = base / repo
        if cand.exists():
            return str(cand)
    return str(base)


def _run_claude(task, cwd, timeout=300):
    exe = _claude()
    if not exe:
        return "Claude-Code-CLI nicht gefunden (npm i -g @anthropic-ai/claude-code)."
    mode = (_cfg().get("autonomy") or "safe").lower()
    perm = ["--dangerously-skip-permissions"] if mode == "full" else ["--permission-mode", "acceptEdits"]
    cmd = ["cmd", "/c", exe, "-p", task] + perm
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip() or (r.stderr or "").strip()
        return out or "Claude hat keine Ausgabe geliefert."
    except subprocess.TimeoutExpired:
        return "Claude arbeitet noch (Zeitlimit erreicht) — schau ins Repo."
    except Exception as e:
        return "Claude Code fehlgeschlagen: " + str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    task = (parameters.get("task") or "").strip()
    if not task:
        return "Was soll Claude coden?"
    cwd = _resolve_dir(parameters.get("repo"))
    timeout = int(_cfg().get("timeout") or 300)
    say = getattr(player, "request_say", None) if player else None
    log = getattr(player, "write_log", None) if player else None

    def worker():
        out = _run_claude(task, cwd, timeout)
        short = out[:600]
        if log:
            try:
                log("JARVIS(Claude): " + short)
            except Exception:
                _swallow_log.debug("ignored error", exc_info=True)
        if say:
            try:
                say("Sag dem Nutzer kurz, dass Claude die Coding-Aufgabe erledigt hat, und fasse das Ergebnis "
                    "in 1-2 Saetzen zusammen: " + short)
            except Exception:
                _swallow_log.debug("ignored error", exc_info=True)

    threading.Thread(target=worker, daemon=True).start()
    where = Path(cwd).name
    return ("Claude arbeitet im Hintergrund an: " + task[:120] +
            " (Ordner: " + where + "). Ich sage Bescheid, sobald es fertig ist.")
