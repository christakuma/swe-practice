"""`practice gc`, as a decision rather than a command.

PLAN.md §8.1 defines an orphan precisely: **a workspace directory with no
corresponding `active` attempt row.** Until Phase 6 there was no attempt table, so
`gc` could see the workspaces and not which of them were in use, and it reported
without ever deleting — because the failure mode of guessing is deleting the
workspace of a session someone has open in another tab.

This is that definition, in the layer the coverage gate and the architecture test
police, over two ports and nothing else. It is here rather than in the CLI command
for one reason: the rule has a consequence that cannot be taken back, so it should
be the thing that is unit-tested against a fake provisioner, not a side effect of a
command that is only exercised end to end.

**The rule is decided on `short_id`.** The workspace directory is named after the
attempt's short id, so an orphan can be identified from the directory name alone —
which is load-bearing rather than convenient. The most interesting leftover is an
interrupted provision whose metadata was never written: it has no `attempt_id` to
match on, and a rule that joined on metadata would classify it as belonging to
nothing *and* be unable to say so for the right reason. Deciding on the name means
the undescribed workspace and the one whose attempt was completed are the same case,
which is what they are.

**Reporting and deleting are one call with a flag, not two use cases.** Because they
must not be able to disagree: a `gc --dry-run` that listed one set and a `gc` that
deleted another is precisely the bug that makes a destructive command untrustworthy.
The same classification is returned either way, and `deleted` says which of it was
acted on.

**Nothing is deleted that is in use, ever, including on an explicit request.** There
is no force flag. An active attempt's workspace is not garbage by any definition,
and a caller that wants it gone abandons the attempt — which is one command, says
what it means, and leaves the attempt marked rather than merely workspace-less.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import Collection, WorkspaceState

if TYPE_CHECKING:
    from practice.domain.ports import AttemptRepository, SandboxProvisioner

__all__ = ["CollectWorkspaces"]


@dataclass(frozen=True, slots=True)
class CollectWorkspaces:
    """Classify every workspace on disk, and optionally delete the orphans."""

    attempts: AttemptRepository
    provisioner: SandboxProvisioner

    def __call__(self, *, delete: bool = False) -> Collection:
        """Report by default. Deleting is the caller's explicit choice.

        The active set is read *before* the workspaces are listed. Both orders are
        racy against a second process and the asymmetry decides it: an attempt that
        starts between the two reads has its workspace appear in a listing taken
        after an active set that does not mention it — and would be deleted. Reading
        the attempts first means such a workspace is simply absent from the listing,
        which is the harmless direction.
        """
        in_use = {attempt.id.short for attempt in self.attempts.active()}
        found = tuple(
            WorkspaceState(workspace=workspace, in_use=workspace.short_id in in_use)
            for workspace in self.provisioner.workspaces()
        )

        deleted: tuple[str, ...] = ()
        if delete:
            deleted = tuple(
                state.workspace.short_id for state in found if state.is_orphan
            )
            for short_id in deleted:
                self.provisioner.discard(short_id)

        return Collection(workspaces=found, deleted=deleted)
