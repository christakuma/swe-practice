"""Reading the exercise library off disk.

Three modules, split by what they know about:

* `schema` — what a valid `exercise.yaml` looks like, as Pydantic models. Knows
  nothing about files.
* `loader` — one exercise directory becomes one `Exercise`. Knows about YAML,
  `notes.md`, and the command lists.
* `filesystem` — the `ContentRepository` port over a content root.

`errors` carries the one exception type the three of them raise, because a
content problem has to be reportable with a path and a line before anything else
it does is useful (PLAN.md §5.4).
"""

from practice.adapters.content.errors import ContentError

__all__ = ["ContentError"]
