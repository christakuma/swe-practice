"""Storage adapters: two implementations of each repository port, on purpose.

`memory` is not a placeholder to be deleted now that `sqlite/` exists — it is the
second implementation that keeps each port honest under the §13 rule, and the one
every application test uses, because an application test that needed a database
would not be an application test. The SQLite side is what the product runs on, and
what proves the port describes something a database can actually do.

The pairing is also what caught a real defect before it existed. The in-memory
attempt store deliberately copies on both `save` and `get`, so a use case that
mutates an aggregate after saving it fails there — rather than passing against a
dict and losing data here, where a row is only what the last `save` wrote.
"""

from practice.adapters.persistence.memory import (
    InMemoryAttemptRepository,
    InMemoryReviewRepository,
)
from practice.adapters.persistence.sqlite import (
    Database,
    SqliteAttemptRepository,
    SqliteReviewRepository,
)

__all__ = [
    "Database",
    "InMemoryAttemptRepository",
    "InMemoryReviewRepository",
    "SqliteAttemptRepository",
    "SqliteReviewRepository",
]
