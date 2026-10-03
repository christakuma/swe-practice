"""Reading the exercise library off disk.

Five modules, split by what each one knows about:

* `schema` — what a valid `exercise.yaml` looks like, as Pydantic models. Knows
  nothing about files.
* `loader` — one exercise directory becomes one `Exercise`. Knows about YAML and
  `notes.md`.
* `validation` — is it a *good* exercise, and do the files it names exist? Knows
  about the command lists and the quality rules.
* `curriculum` — `curriculum.yaml`, the manifest that decides what order the
  library is offered in (Phase 11, ADR 0014). Knows about one small YAML file
  and nothing about exercises beyond their ids.
* `filesystem` — the `ContentRepository` port over a content root.

Loading and validating are separate because the two callers want different
answers: browsing the library should not fail because an exercise someone is
drafting has an empty `notes.md`, while `practice validate` must say so. It is
the same line PLAN.md §4.2 draws inside the domain — a correctness hole is a
failure, a quality rule is a report.

`errors` carries the one exception type they raise, because a content problem
has to be reportable with a path and a line before anything else about it is
useful (PLAN.md §5.4).
"""

from practice.adapters.content.curriculum import (
    CURRICULUM_FILENAME,
    Curriculum,
    Track,
    load_curriculum,
)
from practice.adapters.content.errors import ContentError
from practice.adapters.content.filesystem import FilesystemContentRepository
from practice.adapters.content.loader import load_exercise, load_exercise_file
from practice.adapters.content.validation import (
    ExerciseReport,
    LibraryReport,
    validate_exercise,
    validate_library,
)

__all__ = [
    "CURRICULUM_FILENAME",
    "ContentError",
    "Curriculum",
    "ExerciseReport",
    "FilesystemContentRepository",
    "LibraryReport",
    "Track",
    "load_curriculum",
    "load_exercise",
    "load_exercise_file",
    "validate_exercise",
    "validate_library",
]
