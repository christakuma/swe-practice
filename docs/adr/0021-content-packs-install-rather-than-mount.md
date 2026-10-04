# 0021 — A content pack is installed to a directory, not mounted as a library

- **Status:** accepted
- **Date:** 2026-10-04
- **Phase:** Phase 16

## Context

PLAN.md §11's Phase 13 menu lists *exportable content packs* with one thing in
its **Touches** column: *a content repository adapter*. Phase 15's revision log
went further and nominated it as "the cheapest item on the menu and the only one
that would give a port its second real implementation". Phase 16 was taken to
grade both claims, which is the same reason FSRS was taken first, SQL drills
second and interview mode third.

The §13 half of the claim was true and worth acting on. `ContentRepository` had
`FilesystemContentRepository` and a fake — the arrangement §13 accepts, and the
weakest version of it, because a protocol whose only real implementation is the
one it was extracted from has not been shown to abstract anything. It also had
the thinnest docstring in `ports.py`, which is usually a sign that nobody has
had to think about what it promises.

**The "one adapter" half is where the menu was wrong, and finding out is what
the phase bought.** A pack-backed `ContentRepository` serves a library that can
be listed, filtered, counted, scheduled against and validated — and nothing in
it can be *attempted*. The reason is in `adapters/sandbox/provisioner.py`:

```python
def directory_for(self, exercise_id: ExerciseId) -> Path:
    return self._content_root / exercise_id.value
```

The provisioner is constructed with a `content_root: Path` and reaches exercise
files by path. It has never heard of `ContentRepository`, and it should not:
`pytest` must run a kata's `tests.py` from the workspace, a fixture is bash that
`bash` executes from a file, and `seed.sql` is read by SQLite. Every one of
those needs a real path on a real disk, which §8.1 settled in Phase 3 when it
made the workspace a temporary directory rather than anything more clever.

So the library has **two readers, not one**. The port is the catalogue — what
reads *about* an exercise. The provisioner is the content — what reads the
exercise's files in order to run it. A pack satisfies the first for free and the
second not at all, and no amount of care inside `adapters/content/` changes
that.

## Decision

**A pack is read directly for cataloguing and installed to a directory before
anything is solved from it.** Concretely:

- `PackContentRepository` satisfies `ContentRepository` by reading `exercise.yaml`
  and `notes.md` out of the archive, with nothing extracted. It is a real second
  implementation rather than a wrapper: the parsing goes through
  `loader.parse_exercise_file` and `curriculum.parse_curriculum`, the two
  text-taking functions added for exactly this, and no temporary directory is
  created.
- `install_pack` verifies every digest and then lays the archive out as an
  ordinary content root, which every existing path — provisioner, graders,
  `validate`, `fixtures --check`, `up` — then uses unchanged via
  `--content-root`.
- `ContentRepository` is **not** widened. Its docstring now says it is the
  catalogue and names the provisioner as the other reader, so the next person to
  look does not have to rediscover this.

`practice pack` exposes all three modes — export, `--check`, `--install` —
because ADR 0018's lesson has now repeated three times: a thing nobody can
select is written rather than shipped.

Two supporting decisions the format could not avoid:

- **A pack's `curriculum.yaml` and `fixtures.lock` are derived from its
  selection, not copied.** Both are per-exercise indexes over a whole library,
  so a pack of *part* of one that carried them verbatim installs to a root that
  `practice validate` refuses (a manifest naming exercises that are not there)
  and that `practice fixtures --check` refuses (a lock entry with no exercise).
- **Packs are byte-deterministic.** Fixed entry timestamps, a fixed mode, sorted
  entries, and bytes copied as bytes. A zip records a modification time and a
  unix mode per entry, both of which vary by machine, and the last of those
  matters most: a fixture read in text mode on Windows gains CRLF and then
  builds commit hashes that no longer match the lock file shipped beside it.

## Consequences

**What it buys.** The port has two real implementations and the §13 IOU is
settled for the last port that was carrying one. Both implementations share
`ExerciseFilter.matches` and `curriculum.yaml`, so a packed library and a
directory cannot disagree about order or filtering — and
`tests/integration/content/test_pack_repository.py` compares whole `Exercise`
values to say so. The library becomes something a person can send someone else,
with an integrity check that distinguishes "this file was damaged" from "this
library will not load". And a subset pack is a library in its own right, which
is what makes "here is my SQL track" a sentence the tool can honour.

**What it costs.** Three things, and the first is the real one.

- **There is an extra step, and it is visible to the user.** You cannot point
  `practice up` at a pack. The export/install round trip is two commands rather
  than one, and the `--install` output has to say what to run next because a
  directory appearing is not self-explanatory.
- **A pack is bigger than the library it holds, and goes stale.** It is a copy,
  so an exercise edited in `content/` is not edited in any pack already sent.
  There is no update path and deliberately no attempt at one; re-export is the
  whole story.
- **`adapters/content/pack.py` imports from `adapters/sandbox/`** to reuse the
  lock file's serialiser, which is a content module reaching sideways for the
  first time. It drags the provisioner into the content package's import graph,
  where nothing executes it. The alternative was a second copy of the lock's
  YAML shape, and a format with two writers is a format with two spellings.

**What it does not buy, and this is the honest limit.** The digests are for
corruption and truncation, not tampering. A pack is not signed; anyone who can
rewrite a file inside it can rewrite that file's digest in the manifest. The
`--check` output says "fetch it again" rather than accusing anybody, because
those two cases are genuinely indistinguishable from here and only one of them
is likely.

## Alternatives considered

**Widen `ContentRepository` so a pack can be solved from directly.** The closest
to winning, and the one worth the most words. It means adding something like
`open_file(exercise_id, name) -> bytes` to the port, then changing
`SandboxProvisioner` to take a repository rather than a `content_root` and to
write each file it needs out of the port into the workspace it is building.

Rejected on what it buys against what it reaches. What it buys is skipping an
install step. What it costs is that `provision` — the most carefully bounded
function in the project, and the only place a process starts — grows a second
source of truth for where exercise files come from, and that `adapters/sandbox/`
is modified by a content feature. Worse, **the destination is a directory
either way.** The files still have to be written somewhere `pytest` and `bash`
can reach, so the widened port does not remove the extraction; it moves it
inside `provision` and makes it happen per attempt instead of once. That is the
same work, done more often, in the place where it is hardest to test.

The deciding question was: what would a mounted pack let somebody do that an
installed one does not? The answer is "keep the library as one file on disk",
which is a tidiness preference, not a capability.

**Extract to a temporary directory and delegate to
`FilesystemContentRepository`.** Much less code, and it would satisfy the letter
of §13's two-implementation rule while satisfying none of its purpose. §13 also
says *don't add an abstraction that forwards one call unchanged*, and that is
exactly what this is — a class whose entire behaviour is `extractall` followed
by another class. It would prove that `zipfile` works and nothing about the
port.

**Ship packs as directories, not archives.** A "pack" would be a content root
you copy. Rejected because the thing a pack is *for* is being sent, and a
directory of 357 files is not a thing you send — and because the manifest is
what makes the determinism and integrity claims checkable. A directory has
nowhere to put the digests that is not itself a file in the directory.

**Hold the `ZipFile` open for the repository's lifetime** rather than reading it
in one pass and closing it. Marginally fewer syscalls, and it holds a handle on
a file the user may want to move or delete — which on Windows stops them. The
library is tens of exercises and read-only at runtime, so one pass reads all of
it.

**Sign packs.** Rejected as out of scope and, worse, as a claim this project
cannot back: the tool is offline with no accounts and no key distribution, so a
signature would be checked against a key shipped in the same repository as the
code that checks it. The honest version is the one that ships — digests, and
output that says what they do and do not prove.

**Support `--track` as an export filter** alongside `--kind` and `--difficulty`.
Attractive, because "send me the git track" is the most natural request, and
left out because a track is a `curriculum.yaml` concept rather than an
`ExerciseFilter` one. Adding it means the CLI or the packer learning what a
track is, when `--kind git_scenario` covers the common case. Revisit if somebody
actually asks for a pedagogical track rather than a kind.

## Revisit if

- **A second machine has to stay in sync with a first.** Everything here assumes
  a pack is sent once and re-exported when it changes. A tool that had to
  *update* an installed library would want a diff, a version and a merge rule,
  and none of the three is implied by what is built.
- **An exercise kind arrives whose files are never executed.** The whole
  argument rests on `pytest`, `bash` and SQLite needing real paths. A kind
  graded entirely from `exercise.yaml` would be solvable from a mounted pack,
  and if the library ever became mostly that kind, the widened port stops
  reaching into the sandbox for nothing.
- **Packs start being passed between people who do not trust each other.** Then
  signing is a real requirement rather than a misleading one, and the refusal
  above is the thing to reopen — along with `install_pack`'s path-escape check,
  which is currently a blast-radius guard rather than a security boundary.
