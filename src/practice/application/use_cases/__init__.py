"""One module per use case, each a frozen dataclass of ports with a `__call__`.

Classes rather than functions because the dependencies are injected once and the
call is made many times -- `StartAttempt(content=..., clock=...)` is built by the
composition root and then invoked like a function by whichever adapter is
driving. Functions would mean threading six ports through every call site.

Eight of them, in two groups.

**Four about solving**, two per exercise kind. `StartAttempt` is shared:
provisioning a workspace and building an `Attempt` is the same job whichever kind it
is, which is what the kind registry exists to keep true. Submission is not shared,
because a kata carries source to be saved into the event log and a scenario carries
nothing -- the repository is already on disk and the log already holds every command
that put it there.

**Four about the lifecycle**, added in Phase 6 once an attempt could outlive the
process that started it. `ListOpenAttempts`, `ResumeAttempt` and `AbandonAttempt`
are the resume-or-abandon prompt PLAN.md 8.1 requires on startup -- an interrupted
session is neither silently lost nor silently resurrected -- and
`CollectWorkspaces` is `practice gc`, which could not delete anything until there
was an attempt table to define an orphan against.

Notice that none of the four is kind-specific. The lifecycle of an attempt is the
same whether it is a kata or a git scenario, and the only use cases that have ever
had to care about the difference are the ones that grade.

`GradeReview` joins these in Phase 9.
"""

from practice.application.use_cases.abandon_attempt import AbandonAttempt
from practice.application.use_cases.collect_workspaces import CollectWorkspaces
from practice.application.use_cases.list_open_attempts import ListOpenAttempts
from practice.application.use_cases.resume_attempt import ResumeAttempt
from practice.application.use_cases.run_scenario_command import RunScenarioCommand
from practice.application.use_cases.start_attempt import StartAttempt
from practice.application.use_cases.submit_scenario import SubmitScenario
from practice.application.use_cases.submit_solution import SubmitSolution

__all__ = [
    "AbandonAttempt",
    "CollectWorkspaces",
    "ListOpenAttempts",
    "ResumeAttempt",
    "RunScenarioCommand",
    "StartAttempt",
    "SubmitScenario",
    "SubmitSolution",
]
