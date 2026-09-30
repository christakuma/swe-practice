"""Pure domain: data and functions, no I/O.

Nothing under this package may import `subprocess`, `sqlite3`, `httpx`, or
anything from `practice.adapters` / `practice.interface`. Ports are declared
here as `typing.Protocol` and implemented outward (PLAN.md §4.6).
"""
