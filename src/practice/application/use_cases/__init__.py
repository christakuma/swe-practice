"""One module per use case, each a frozen dataclass of ports with a `__call__`.

Classes rather than functions because the dependencies are injected once and the
call is made many times -- `StartAttempt(content=..., clock=...)` is built by the
composition root and then invoked like a function by whichever adapter is
driving. Functions would mean threading six ports through every call site.

Seventeen of them, in five groups.

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
the log beside the commands they ran, because the grade suggestion reads it --
"passed, but with three of four hints" is a different outcome from "passed". That is
why it is a use case and not a property on the workbench DTO.

**Three about scheduling**, Phase 9's own group and the one that turns a pile of
verdicts into a training system. `OfferReview` reads what the tool would grade a
finished attempt; `GradeReview` moves the card, taking the suggestion when no grade
is given; `ReviewQueue` answers *what should I practise today* by joining the card
store against the whole library, because an exercise with no card is the most
common due item there is.

`SummariseProgress` joins them and is the only read in the group that touches the
attempt log: what is *due* is a question about cards and the library, and how it
is *going* is a question about everything that has been graded.

**Two about working somewhere else**, both Phase 10's. `RevealSolutionFile` is
the only use case whose output is a filesystem path: own-editor mode's premise is
that a kata's solution is a real file in the workspace, so the thing a page or a
terminal needs is where it is. It refuses a git scenario, which is the mirror of
`InspectRepository` refusing a kata — one kind has a file to edit and the other
has a repository to interrogate, and neither question applies to both. They
share `load_solution_file`, for the reason `OfferReview` and `GradeReview` share
`load_offer`: a page that offered the first on attempts the second refuses would
be a page with a button that does nothing.

`WatchSolutionFile` is the odd one in the whole set and worth reading as the
exception it is. It is the only use case that is a *stream* rather than a call,
and the only one that grades without recording anything: a save is not a
submission, so the attempt is handed the source in memory, graded, and thrown
away (ADR 0013). Everything else here either reads or writes; this one does
neither, on purpose.

`OfferReview` and `GradeReview` share `load_offer` rather than one calling the
other. They have to agree about whether an attempt has already been reviewed --
the panel hides the buttons on exactly the attempts the post refuses -- and a use
case holding a use case would have given the same answer while putting a second
decision in the composition root about which of them owns the repositories.
"""

from practice.application.use_cases.abandon_attempt import AbandonAttempt
from practice.application.use_cases.collect_workspaces import CollectWorkspaces
from practice.application.use_cases.grade_review import GradeReview
from practice.application.use_cases.inspect_repository import InspectRepository
from practice.application.use_cases.list_open_attempts import ListOpenAttempts
from practice.application.use_cases.offer_review import OfferReview
from practice.application.use_cases.open_workbench import OpenWorkbench
from practice.application.use_cases.resume_attempt import ResumeAttempt
from practice.application.use_cases.reveal_hint import RevealHint
from practice.application.use_cases.reveal_solution_file import RevealSolutionFile
from practice.application.use_cases.review_queue import ReviewQueue
from practice.application.use_cases.run_scenario_command import RunScenarioCommand
from practice.application.use_cases.start_attempt import StartAttempt
from practice.application.use_cases.submit_scenario import SubmitScenario
from practice.application.use_cases.submit_solution import SubmitSolution
from practice.application.use_cases.summarise_progress import SummariseProgress
from practice.application.use_cases.watch_solution_file import WatchSolutionFile

__all__ = [
    "AbandonAttempt",
    "CollectWorkspaces",
    "GradeReview",
    "InspectRepository",
    "ListOpenAttempts",
    "OfferReview",
    "OpenWorkbench",
    "ResumeAttempt",
    "RevealHint",
    "RevealSolutionFile",
    "ReviewQueue",
    "RunScenarioCommand",
    "StartAttempt",
    "SubmitScenario",
    "SubmitSolution",
    "SummariseProgress",
    "WatchSolutionFile",
]
