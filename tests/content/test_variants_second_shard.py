"""The other half of the variants, graded beside the first rather than after it.

`test_variants.py` has the argument; this file exists only so that the
argument has somewhere to put the second share. Everything a variant is held
to is imported from where it is defined -- the kata tests from `test_katas.py`,
and from `test_variants.py` the one it adds, that a variant's base solution
must fail it -- and the fixture that says *which directories* is overridden
again, exactly as that file overrides it.

**It also holds the one claim sharding introduces**: that between them the
files grade every variant. The shards are slices of one list and cannot
overlap or leave a gap on their own, so what the test guards is the count --
`SHARDS` raised to three with no third file, or a file added that asks for a
share nobody defined. It lives here rather than there because this file can
import that one and the reverse would be a cycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.content import test_variants as first_shard

# The fixtures are imported for pytest to find, and the tests to be collected
# here over the directories below.
from tests.content.test_katas import (  # noqa: F401
    _identify,
    exercise,
    git,
    grade,
    spec,
    stub_verdict,
    test_it_shows_more_than_one_example,
    test_it_states_its_constraints,
    test_its_declared_complexity_is_compared_rather_than_graded,
    test_its_examples_give_the_output_they_show,
    test_its_hidden_suite_holds_more_than_one_test,
    test_its_reference_solution_passes_every_check,
    test_its_stub_fails,
)
from tests.content.test_variants import (  # noqa: F401
    shard,
    test_its_base_solution_does_not_pass_it,
)

if TYPE_CHECKING:
    from pathlib import Path

VARIANT_DIRECTORIES = shard(1)

#: Every module that grades a share, in shard order.
_SHARES = (first_shard.VARIANT_DIRECTORIES, VARIANT_DIRECTORIES)


@pytest.fixture(params=VARIANT_DIRECTORIES, ids=_identify)
def kata_directory(request: pytest.FixtureRequest) -> Path:
    """The override: the imported tests ask for this by name and get a variant."""
    directory: Path = request.param
    return directory


def test_there_are_variants_to_grade() -> None:
    """Without this, every parametrized test in this file is vacuously true."""
    assert VARIANT_DIRECTORIES


def test_the_files_grade_every_variant_between_them() -> None:
    """One file per shard, and every variant in exactly one of them.

    A variant that no file parametrizes over is graded by nothing, and
    nothing else in the suite would say so: `practice validate` would still
    load it, and the library tests would still find it offered under its
    base.
    """
    graded = [directory for share in _SHARES for directory in share]

    assert len(_SHARES) == first_shard.SHARDS
    assert len(graded) == len(set(graded))
    assert sorted(graded) == sorted(first_shard.ALL_VARIANT_DIRECTORIES)
