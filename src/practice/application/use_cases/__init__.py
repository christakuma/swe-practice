"""One module per use case, each a frozen dataclass of ports with a `__call__`.

Classes rather than functions because the dependencies are injected once and the
call is made many times — `StartAttempt(content=..., clock=...)` is built by the
composition root and then invoked like a function by whichever adapter is
driving. Functions would mean threading six ports through every call site.

`RunScenarioCommand` and `SubmitScenario` join these in Phase 5, and
`GradeReview` in Phase 9.
"""

from practice.application.use_cases.start_attempt import StartAttempt
from practice.application.use_cases.submit_solution import SubmitSolution

__all__ = ["StartAttempt", "SubmitSolution"]
