"""Test package.

A package rather than a bare directory so `tests.fakes` is importable from every
suite; `pythonpath = ["."]` in pyproject puts the project root on `sys.path` for
that import. The alternative — fakes declared as conftest fixtures — makes them
invisible to mypy, which is where the port conformance in `tests/unit/
test_ports.py` is actually checked.
"""
