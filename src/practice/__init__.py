"""swe-practice: an offline practice environment for katas and operational git.

Layering (PLAN.md §3) — dependencies point inward, and `tests/unit/
test_architecture.py` fails the build if that is ever violated:

    interface/ -> application/ -> domain/ <- adapters/

`composition.py` is the only module permitted to import across all layers.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
