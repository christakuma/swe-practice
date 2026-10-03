"""One module per use case, each a frozen dataclass of ports with a `__call__`.

Classes rather than functions because the dependencies are injected once and the
call is made many times -- `StartAttempt(content=..., clock=...)` is built by the
composition root and then invoked like a function by whichever adapter is
driving. Functions would mean threading six ports through every call site.

Eleven of them, in three groups.

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

**Two about display**, added with the web app. `OpenWorkbench` (Phase 7) loads an
attempt for a *page* rather than for a session, which is a question the CLI never
had to ask: `practice submit` prints a verdict and the attempt is done with, while
`/attempt/{id}` is a tab someone left open across that submission and has to render
either way. `ResumeAttempt` refuses a finished attempt, correctly -- resuming one is
not a thing that can happen -- so bending it to cover this would have made it two
use cases wearing one name.

`InspectRepository` is Phase 8's addition and is the same kind of read.
It answers the repo state panel *through the same `RepoQuery` the grader reads
through*, so the panel a solver decides to submit from cannot disagree with the
verdict they then get.

**One that looks like display and is not.** `RevealHint` renders a fragment, and it
writes: revealing a hint is something the solver *did* in the exercise, recorded in
the log beside the commands they ran, because Phase 9's grade suggestion reads it --
"passed, but with three of four hints" is a different outcome from "passed". That is
why it is a use case and not a property on the workbench DTO.

`GradeReview` joins these in Phase 9.
"""

from practice.application.use_cases.abandon_attempt import AbandonAttempt
from practice.application.use_cases.collect_workspaces import CollectWorkspaces
from practice.application.use_cases.inspect_repository import InspectRepository
from practice.application.use_cases.list_open_attempts import ListOpenAttempts
from practice.application.use_cases.open_workbench import OpenWorkbench
from practice.application.use_cases.resume_attempt import ResumeAttempt
from practice.application.use_cases.reveal_hint import RevealHint
from practice.application.use_cases.run_scenario_command import RunScenarioCommand
from practice.application.use_cases.start_attempt import StartAttempt
from practice.application.use_cases.submit_scenario import SubmitScenario
from practice.application.use_cases.submit_solution import SubmitSolution

__all__ = [
    "AbandonAttempt",
    "CollectWorkspaces",
    "InspectRepository",
    "ListOpenAttempts",
    "OpenWorkbench",
    "ResumeAttempt",
    "RevealHint",
    "RunScenarioCommand",
    "StartAttempt",
    "SubmitScenario",
    "SubmitSolution",
]
