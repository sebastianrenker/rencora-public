"""
Rencora GitHub knowledge — lets Rencora answer anything about the owner's GitHub.

Reads the public GitHub API for the configured user. Set your GitHub username in
config/owner.json ("github") or config/github.json ({ "username": "your-handle" }).

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

_CFGDIR = Path(__file__).resolve().parent.parent / "config"


def _username():
    # owner.json is the source of truth; github.json is a fallback.
    for fname, key in (("owner.json", "github"), ("github.json", "username")):
        try:
            u = json.loads((_CFGDIR / fname).read_text(encoding="utf-8")).get(key, "")
            if u:
                return u.strip()
        except Exception:
            pass
    return ""   # nicht konfiguriert → run() bittet den Nutzer, den GitHub-Namen zu setzen


PLUGIN = {
    "name": "github_info",
    "description": (
        "Answer ANY question about the owner's GitHub account and projects: "
        "list repositories, a repo's description/language/stars, what a project does, recent "
        "activity. Use for: 'meine Projekte', 'was hab ich auf GitHub', 'erzähl mir über mein "
        "Repo X', 'welche Sprachen nutze ich', GitHub, Repository, Projekte."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "repos (list all) | repo (facts, needs repo_name) | readme (what a repo does, needs repo_name) | profile"},
            "repo_name": {"type": "STRING", "description": "Repository name (for action=repo/readme)"},
        },
        "required": [],
    },
}


def _get(url):
    if requests is None:
        return None, "Das GitHub-Modul braucht das requests-Paket."
    try:
        r = requests.get(url, headers={"Accept": "application/vnd.github+json",
                                       "User-Agent": "Rencora"}, timeout=12)
        if r.status_code == 404:
            return None, "Nicht gefunden."
        if r.status_code == 403:
            return None, "GitHub-Limit erreicht, bitte kurz später erneut."
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, "GitHub nicht erreichbar: " + str(e)


def _profile(u):
    d, err = _get("https://api.github.com/users/" + u)
    if err:
        return err
    parts = ["GitHub @" + u]
    if d.get("public_repos") is not None:
        parts.append(str(d["public_repos"]) + " oeffentliche Repositories")
    if d.get("followers") is not None:
        parts.append(str(d["followers"]) + " Follower")
    if d.get("bio"):
        parts.append("Bio: " + d["bio"])
    return ", ".join(parts) + "."


def _repos(u):
    d, err = _get("https://api.github.com/users/" + u + "/repos?per_page=100&sort=updated")
    if err:
        return err
    if not d:
        return "Ich finde keine oeffentlichen Repositories fuer @" + u + "."
    d = [r for r in d if not r.get("fork")]
    items = []
    for r in d[:12]:
        s = r.get("name", "")
        if r.get("language"):
            s += " (" + r["language"] + ")"
        if r.get("description"):
            s += " - " + r["description"]
        items.append(s)
    head = "@" + u + " hat " + str(len(d)) + " eigene Repositories. Die aktuellsten: "
    return head + "; ".join(items) + "."


def _repo(u, name):
    if not name:
        return "Welches Repository meinst du?"
    d, err = _get("https://api.github.com/repos/" + u + "/" + name)
    if err:
        return "Repository '" + name + "': " + err
    parts = ["Repository " + d.get("name", name)]
    if d.get("description"):
        parts.append(d["description"])
    facts = []
    if d.get("language"):
        facts.append("Sprache " + d["language"])
    if d.get("stargazers_count") is not None:
        facts.append(str(d["stargazers_count"]) + " Sterne")
    if d.get("open_issues_count") is not None:
        facts.append(str(d["open_issues_count"]) + " offene Issues")
    if facts:
        parts.append(", ".join(facts))
    return ". ".join(parts) + "."


def _readme(u, name):
    if not name:
        return "Welches Repository meinst du?"
    d, err = _get("https://api.github.com/repos/" + u + "/" + name + "/readme")
    if err:
        return "README von '" + name + "': " + err
    try:
        import base64
        text = base64.b64decode(d.get("content", "")).decode("utf-8", "replace")
    except Exception:
        return "Die README von " + name + " konnte nicht gelesen werden."
    # trim markdown noise, keep the essence for the assistant to summarise
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln.lstrip("#>*-` ").strip() for ln in lines if ln and not ln.startswith(("![", "[!", "<img", "|"))]
    body = " ".join(lines)
    if len(body) > 900:
        body = body[:900] + " …"
    return "README von " + name + ": " + body


def run(parameters: dict, player=None, session_memory=None) -> str:
    u = _username()
    if not u:
        return ("Es ist kein GitHub-Nutzer konfiguriert. Trage deinen GitHub-Namen in "
                "config/owner.json ('github') oder config/github.json ('username') ein.")
    action = (parameters.get("action") or "repos").strip().lower()
    try:
        if action == "profile":
            out = _profile(u)
        elif action == "repo":
            out = _repo(u, (parameters.get("repo_name") or "").strip())
        elif action == "readme":
            out = _readme(u, (parameters.get("repo_name") or "").strip())
        else:
            out = _repos(u)
    except Exception as e:
        return "Die GitHub-Abfrage ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            pass
    return out
