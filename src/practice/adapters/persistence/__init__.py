"""Storage adapters.

`memory` is here now; `sqlite/` joins it in Phase 6, behind the same ports. The
in-memory store is not a placeholder to be deleted when SQLite lands — it is the
second implementation that keeps `AttemptRepository` honest under the §13 rule,
and the one every application test uses, because an application test that
needed a database would not be an application test.
"""

from practice.adapters.persistence.memory import InMemoryAttemptRepository

__all__ = ["InMemoryAttemptRepository"]
