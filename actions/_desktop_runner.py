"""Child-process entry point for generated desktop code.

Started by actions/desktop.py as ``python -E -s _desktop_runner.py <repo-root>``;
the (already statically checked) code arrives on stdin and the result text is
written to stdout. Keeping this in its own process lets the parent enforce a
time limit and hand over a scrubbed environment.
"""
import sys


def main() -> int:
    root = sys.argv[1]
    if root not in sys.path:
        sys.path.insert(0, root)
    code = sys.stdin.read()

    import contextlib

    from actions import desktop  # noqa: E402

    # Diagnostics printed by the helper go to stderr; stdout carries only the result.
    with contextlib.redirect_stdout(sys.stderr):
        result = desktop._run_in_namespace(code)
    sys.stdout.buffer.write(result.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
