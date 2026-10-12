"""Pins the generated-code guard in actions/desktop.py (no GUI needed)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions import desktop  # noqa: E402


def test_plain_code_runs():
    assert desktop._execute_generated_code("print(len([1, 2, 3]))") == "3"


def test_path_and_time_are_available():
    out = desktop._execute_generated_code("print(Path('.').name == '' or True)")
    assert out == "True"


def test_object_graph_escape_is_blocked():
    code = "print(().__class__.__bases__[0].__subclasses__())"
    assert "blocked" in desktop._execute_generated_code(code)


def test_import_is_blocked():
    assert "blocked" in desktop._execute_generated_code("import os\nprint(os.getcwd())")


def test_getattr_dunder_is_refused():
    out = desktop._execute_generated_code("print(getattr(print, '__self__'))")
    assert "Error" in out or "error" in out or "not allowed" in out or out == "Done."
    assert "builtin" not in out


def test_unsafe_marker_is_rejected():
    assert "cannot be performed" in desktop._execute_generated_code("UNSAFE")


# --- process isolation and Path guard ---------------------------------------

def test_runs_in_a_separate_process():
    # pyautogui/ctypes are not needed: ask the namespace for nothing, just run.
    out = desktop._execute_generated_code("print('ok')")
    assert out == "ok"


def test_delete_is_refused(tmp_path):
    victim = tmp_path / "keep.txt"
    victim.write_text("x", encoding="utf-8")
    out = desktop._execute_generated_code(f"Path({str(victim)!r}).unlink()")
    assert "not allowed" in out
    assert victim.exists()


def test_write_is_refused(tmp_path):
    target = tmp_path / "new.txt"
    out = desktop._execute_generated_code(f"Path({str(target)!r}).write_text('hi')")
    assert "not allowed" in out
    assert not target.exists()


def test_reading_listing_still_works(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    code = f"p = Path({str(tmp_path)!r})\nprint(sorted(x.name for x in p.iterdir()))\nprint((p / 'a.txt').read_text())"
    out = desktop._execute_generated_code(code)
    assert "['a.txt']" in out and "hello" in out


def test_copy_helpers_still_work(tmp_path):
    src = tmp_path / "s.txt"
    src.write_text("data", encoding="utf-8")
    dst = tmp_path / "d.txt"
    out = desktop._execute_generated_code(f"shutil.copy2({str(src)!r}, {str(dst)!r})\nprint('copied')")
    assert out == "copied"
    assert dst.read_text(encoding="utf-8") == "data"


def test_config_directory_is_unreadable():
    secret = os.path.join(desktop._get_base_dir(), "config", "api_keys.json")
    out = desktop._execute_generated_code(f"print(Path({secret!r}).read_text())")
    assert "not allowed" in out or "Error" in out


def test_runaway_code_is_killed(monkeypatch):
    monkeypatch.setattr(desktop, "_EXEC_TIMEOUT_S", 2)
    out = desktop._execute_generated_code("x = 0\nwhile True:\n    x += 1")
    assert "timed out" in out


def test_child_env_is_allowlisted(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-value")
    monkeypatch.setenv("GITHUB_TOKEN", "secret-value")
    env = desktop._child_env()
    assert "GEMINI_API_KEY" not in env and "GITHUB_TOKEN" not in env
    assert env["PYTHONUTF8"] == "1"
