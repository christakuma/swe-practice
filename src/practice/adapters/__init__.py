"""Adapters: everything that touches git, the filesystem, SQLite, or a clock.

Adapters may import the domain. Nothing in the domain may import an adapter, and
`tests/unit/test_architecture.py` fails the build if that is ever violated
(ADR 0002).
"""
