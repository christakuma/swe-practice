"""Driving adapters: the ways a person reaches the application.

Two of them, deliberately. The web app is the real interface — commit graphs
and diffs are painful in a terminal — and the Typer CLI is the proof that the
hexagonal boundary is real rather than decorative: a core secretly coupled to
HTTP would not survive a second driving adapter (PLAN.md §2).
"""
