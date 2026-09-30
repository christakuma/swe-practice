"""Domain error types.

Two shapes, and the split is load-bearing rather than taxonomy for its own
sake.

`InvalidValueError` means a value object was handed something it cannot
represent. It subclasses `ValueError` as well as `DomainError` **deliberately**:
Phase 2's Pydantic schema constructs these value objects inside field
validators, and Pydantic turns a `ValueError` raised there into a proper
validation error with the field path attached. Without that second base class,
every invariant expressed in the domain would have to be restated in the schema
layer just to produce a readable message — and the two copies would drift.

`AttemptStateError` and `PolicyViolationError` are failures of a live aggregate,
not bad input, so they stay off `ValueError`. Keeping them distinct lets the web
layer answer differently: a state error is a stale page that should be
re-rendered, a policy violation is a message to show the user.
"""

from __future__ import annotations

__all__ = [
    "AttemptStateError",
    "DomainError",
    "InvalidValueError",
    "PolicyViolationError",
]


class DomainError(Exception):
    """Base class for every error raised from `practice.domain`."""


class InvalidValueError(DomainError, ValueError):
    """A value object was given data it cannot represent."""


class AttemptStateError(DomainError):
    """An operation was attempted against an attempt in the wrong state."""


class PolicyViolationError(DomainError):
    """An operation exceeded the limits the `AttemptPolicy` carries."""
