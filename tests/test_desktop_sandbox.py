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
