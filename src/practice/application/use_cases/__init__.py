"""One module per use case, each a frozen dataclass of ports with a `__call__`.

Classes rather than functions because the dependencies are injected once and the
call is made many times -- `StartAttempt(content=..., clock=...)` is built by the
composition root and then invoked like a function by whichever adapter is
driving. Functions would mean threading six ports through every call site.

Four of them, two per exercise kind. `StartAttempt` is shared: provisioning a
workspace and building an `Attempt` is the same job whichever kind it is, which is
what the kind registry exists to keep true. Submission is not shared, because a
kata carries source to be saved into the event log and a scenario carries nothing
-- the repository is already on disk and the log already holds every command that
put it there.

`GradeReview` joins these in Phase 9.
"""

from practice.application.use_cases.run_scenario_command import RunScenarioCommand
from practice.application.use_cases.start_attempt import StartAttempt
from practice.application.use_cases.submit_scenario import SubmitScenario
from practice.application.use_cases.submit_solution import SubmitSolution

__all__ = [
    "RunScenarioCommand",
    "StartAttempt",
    "SubmitScenario",
    "SubmitSolution",
]
