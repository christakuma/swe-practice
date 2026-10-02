# Architecture decision records

One file per decision, numbered, append-only. Written when the decision is
made — not reconstructed afterwards, because a retrofitted ADR records the
justification and loses the alternatives, which is the half worth keeping.

## Process

1. Copy [`template.md`](template.md) to `NNNN-short-title.md`, next number up.
   Numbers are never reused, and a file is never deleted.
2. Open it as `proposed` if it is still being argued, `accepted` if it is not.
3. A decision that is reversed gets a **new** ADR. The old one is marked
   `superseded by ADR-NNNN` and its text is left exactly as it was — the point
   of the record is what was believed at the time.
4. Add it to the index below and to the table in [PLAN.md §12](../PLAN.md).

Scope: decisions that are expensive to reverse or that a reader would otherwise
have to reverse-engineer from the code. Library choices that could be swapped in
an afternoon do not need one.

## Index

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted |
| [0002](0002-ports-and-adapters-with-an-enforced-boundary.md) | Ports and adapters, with the boundary enforced by a test | accepted |
| [0003](0003-grade-git-exercises-by-repo-state.md) | Grade git exercises by repo state, not command text | accepted |
| [0004](0004-content-as-declarative-data.md) | Content is declarative data, validated by schema | accepted |
| [0005](0005-sandbox-via-temp-dirs-and-subprocess.md) | Sandbox via a scoped directory and subprocess, not containers | accepted |
| [0006](0006-sqlite-without-an-orm.md) | SQLite with hand-written SQL and explicit mappers, not an ORM | accepted |
| [0011](0011-reference-solutions-are-command-lists.md) | Reference solutions are command lists, not shell scripts | accepted |

0011 is out of sequence because the number was reserved for it in PLAN.md §12
before the decision was written up, and numbers are never reused. 0007–0010 are
the ones still to come.

Planned, not yet written (PLAN.md §12): HTMX over an SPA · SM-2 first with FSRS
behind a port · ship our own prompts · CodeMirror 5 over 6.
