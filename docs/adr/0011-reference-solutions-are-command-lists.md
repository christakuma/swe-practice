# 0011 — Reference solutions are command lists, not shell scripts

- **Status:** accepted
- **Date:** 2026-10-01
- **Phase:** 5 (decided in the pre-Phase-0 review; written before the engine
  started replaying these lists, which is the point at which it became hard to
  reverse)

## Context

[ADR 0003](0003-grade-git-exercises-by-repo-state.md) commits the project to
grading the end state of a real repository, and [ADR
0005](0005-sandbox-via-temp-dirs-and-subprocess.md) to executing a learner's
commands through `subprocess` with an **argv list and no shell**. A solver's
input is parsed into an argv, vetted against the exercise's `allowed_commands`,
and handed to a process; shell metacharacters are rejected before anything runs,
and file operations go through virtual commands (`write`, `append`, `rm`,
`mkdir`) implemented in Python.

Every git scenario also ships a reference answer, and CI has to prove it works.
That forces a question about the *form* of that answer, and the first draft of
the plan got it wrong.

As originally designed, a scenario shipped `solution.sh` — a bash script, run the
way a fixture is run, because a fixture is trusted code and gets a real shell.
The consequence was not noticed until PLAN.md's review pass: **CI would have
validated reference solutions through an execution path no solver can use.**

A green build would then have proved that *a* solution exists. It would not have
proved that a solution exists **within the rules the solver is held to**. The gap
is not hypothetical, because the rules are genuinely narrower than bash:

- no pipes, no redirection, no `&&`, no command substitution;
- only the programs in the exercise's own `allowed_commands`;
- a command budget;
- `write` takes its content as a single argv element, so multi-line file content
  cannot be expressed the way a heredoc would express it.

A reference solution written in bash will reach for all of those without its
author noticing, because bash is where one naturally writes git. The failure mode
is a **scenario that ships unsolvable with a green build** — and it would be found
by the first learner who tried it, not by the suite.

There is a second, quieter reason. The reference answer is also the worked example
a content author reads when writing the next exercise. If it is written in a
dialect the learner cannot type, it teaches the wrong dialect.

## Decision

A scenario's reference answer and every counter-example are **`.cmds` files: one
command per line, `#` comments and blank lines ignored, nothing else.** They are
replayed through the same path a solver's input takes, and that is enforced in
three places rather than trusted:

1. **One parser.** `domain/commands.py` holds `parse_command_line` and
   `parse_command_list`, and it is the only thing that turns a typed line into an
   argv. The content validator and the sandbox call the same function. A second
   copy is the specific failure this ADR exists to prevent, so there is not one.
2. **`practice validate` checks every line against the exercise's own
   `allowed_commands`**, offline and without running anything. An author gets the
   error while editing rather than from CI.
3. **The content suite replays every list through the real use cases.**
   `tests/content/test_fixtures.py` asserts every line of the reference *runs*;
   `tests/content/test_scenarios.py` grades the end state and asserts each
   counter-example fails exactly the checks it declares. Both go through
   `RunScenarioCommand`, which applies the policy, the allowlist and the budget —
   so the thing CI proves is the thing a learner can do.

Comments are whole-line only: a `#` is stripped when it is the first
non-whitespace character and is an ordinary argument character anywhere else.
Trailing comments would be friendlier right up until the first
`git log --format=%h#%s`, and a format string that silently loses half of itself
is a worse failure than not being allowed to annotate a line.

Fixtures are **unchanged** and remain bash scripts. They are trusted code written
by the exercise author, they run before the attempt begins, and they need a real
shell to build a repository worth practising on. The trust split is the whole
point: *fixtures are trusted code, solver commands are untrusted input*, and this
ADR is about which side the reference answer falls on. It falls on the solver's
side, because it is a claim about what a solver can do.

## Consequences

**CI proves solvability, not merely existence.** This is the entire return. A
scenario cannot ship whose reference answer depends on an affordance the learner
does not have, because the audit and the grading both run through the learner's
path.

**The reference answer is a worked example in the right dialect.** A content
author reading `solution.cmds` sees the commands a solver would type, including
the virtual ones. That is also what makes the files worth printing in a hint or a
post-attempt explanation later.

**The fidelity guarantee has been tested, not asserted.** Every line of every
reference and counter-example in the library passes the real policy, and the
graded replay in Phase 5 found a real defect on its first run — a counter-example
under-declaring its failures — which is the class of rot this arrangement exists
to make visible.

**Cost: some scenarios become harder to author, and a few become impossible.**
Anything needing multi-line file content cannot be expressed, because `write`
takes one argv element. Merge-conflict resolution is the concrete casualty, and
PLAN.md §15 records it as an open question: it probably needs the CodeMirror
editing pane rather than a command list, which is a Phase 8 decision. This ADR
makes that constraint *visible* instead of letting a bash reference solution hide
it until a learner hits it.

**Cost: a reference answer is less expressive than the thing an author would
write by hand.** No loops, no variables, no conditionals. In practice this has not
bitten — a scenario's answer is a handful of commands — and if it did, the honest
response would be that the exercise is too large rather than that the format is
too small.

**Cost: one more file format with its own parser and its own tests.** Small, and
paid for by the first scenario.

## Alternatives considered

**`solution.sh` as a bash script, run like a fixture.** The original design, and
the one this record exists to reject. Rejected because it validates through a path
the learner cannot use, which means a green build is compatible with an unsolvable
exercise. It is also the most convenient option, which is why it was chosen first
and why the rejection is worth recording rather than assuming.

**A bash script, but linted to the policy.** Parse the script and reject anything
the policy would reject. Rejected because it is the same work as the command-list
parser plus a bash parser, and because the two would disagree: a linter that
understood enough bash to be useful would understand constructs the sandbox
cannot run, and the places they diverge are exactly where a scenario would ship
broken.

**Admit a shell for solvers, so the two paths converge from the other end.**
Rejected on ADR 0005's reasoning and one more of its own. `echo x > build.sh`
would then work, and a learner practising operational git would be learning shell
redirection in a tool whose web console cannot offer a shell either. Converging on
the narrower path keeps the CLI and the web surface identical, which is the
property that makes the CLI a real second driving adapter rather than a
convenience.

**No reference answer at all; trust the author.** Rejected outright. PLAN.md §13
rates "assertions too loose to tell right from wrong" as a high risk, and a
reference solution that CI grades is half the mitigation — the counter-examples
are the other half. An exercise nobody has proved solvable is an exercise that is
not finished.

**A reference answer expressed as expected *end state* rather than commands.**
Interesting, and rejected for now: it would prove the checks are satisfiable
without proving they are *reachable*, which is the more useful claim. It would also
need a way to author a repository state directly, which is a second fixture format.

## Revisit if

- **Merge-conflict scenarios are built and `.cmds` cannot express them.** The
  likely trigger. If resolving a conflict needs the editor pane, a scenario's
  answer is no longer purely a list of commands, and the format has to grow a way
  to say "and then the file looked like this" — most likely a sibling file the
  list references, so the commands stay commands.
- **A learner-facing shell is ever admitted.** Then the two paths converge and
  this ADR is moot. ADR 0005 would have to be superseded first.
- **An exercise genuinely needs a loop or a conditional in its answer.** That is
  more likely to mean the exercise is too large, but if it recurs, the answer is
  not to reach for bash — it is to ask why a learner would be expected to type
  one.
