"""`path_writable`, and the kernel's permission rule under it.

The case worth reading first is `TestMay::test_the_owner_bits_win_even_when_
narrower`: a model that checked *any* matching class would let the owner of a
`chmod 077` directory write it, and the kernel does not.
"""

from __future__ import annotations

from dataclasses import replace

from practice.domain.containers.ownership import READ, SEARCH, WRITE, may
from practice.domain.ports import Account, PathAccess, PathEntry
from tests.fakes.build import FakeBuildQuery, a_directory, an_account
from tests.unit.domain.containers.helpers import run

APP = an_account("app", 1000, 1000)
ROOT_DIR = a_directory("/")
APP_DIR = a_directory("/app", at=3)


def image(access: PathAccess, *accounts: Account) -> FakeBuildQuery:
    return FakeBuildQuery(
        user="app", accounts=[APP, *accounts], paths={"/app/data": access}
    )


def reach(
    *chain: PathEntry,
    exists: bool = True,
    notes: tuple[str, ...] = (),
    stopped: str | None = None,
) -> PathAccess:
    return PathAccess(chain=chain, exists=exists, notes=notes, stopped=stopped)


def a_file(entry: PathEntry) -> PathEntry:
    return replace(entry, directory=False)


class TestMay:
    def test_root_may_do_anything(self) -> None:
        locked = a_directory("/x", owner=(5, 5), mode=0o000)
        assert may(an_account("root", 0), locked, WRITE | SEARCH)

    def test_the_owner_reads_the_owner_bits(self) -> None:
        mine = a_directory("/x", owner=(1000, 0), mode=0o700)
        assert may(APP, mine, READ | WRITE | SEARCH)

    def test_the_owner_bits_win_even_when_narrower(self) -> None:
        mine = a_directory("/x", owner=(1000, 1000), mode=0o077)
        assert not may(APP, mine, WRITE)

    def test_a_member_reads_the_group_bits(self) -> None:
        shared = a_directory("/x", owner=(0, 1000), mode=0o770)
        assert may(APP, shared, WRITE | SEARCH)
        assert not may(APP, a_directory("/x", owner=(0, 1000), mode=0o750), WRITE)

    def test_anyone_else_reads_the_other_bits(self) -> None:
        assert may(APP, a_directory("/shared", mode=0o1777), WRITE | SEARCH)
        assert not may(APP, a_directory("/x"), WRITE)


class TestPathWritable:
    def test_passes_a_directory_the_user_owns(self) -> None:
        owned = a_directory("/app/data", owner=(1000, 1000), at=6)
        report = run(
            "path_writable", image(reach(ROOT_DIR, APP_DIR, owned)), path="/app/data"
        )
        assert report.passed
        assert report.expected == "the user the image runs as can write /app/data"
        assert report.actual == (
            "'app' can write /app/data (1000:1000, mode 755, set on line 6)"
        )

    def test_fails_a_root_owned_directory(self) -> None:
        theirs = a_directory("/app/data", at=4)
        report = run(
            "path_writable", image(reach(ROOT_DIR, APP_DIR, theirs)), path="/app/data"
        )
        assert not report.passed
        assert report.actual == (
            "'app' (uid 1000) cannot write /app/data (0:0, mode 755, set on line 4)"
        )

    def test_a_missing_path_needs_a_parent_it_can_write(self) -> None:
        mine = a_directory("/app", owner=(1000, 1000), at=3)
        report = run(
            "path_writable",
            image(reach(ROOT_DIR, mine, exists=False)),
            path="/app/data",
        )
        assert report.passed
        assert (report.actual or "").startswith(
            "/app/data does not exist yet, and 'app'"
        )

    def test_a_missing_path_under_root_s_directory_fails(self) -> None:
        report = run(
            "path_writable",
            image(reach(ROOT_DIR, APP_DIR, exists=False)),
            path="/app/data",
        )
        assert not report.passed
        assert report.actual == (
            "'app' (uid 1000) cannot create /app/data in /app (0:0, mode 755, "
            "set on line 3)"
        )

    def test_a_file_needs_only_the_write_bit(self) -> None:
        ledger = a_directory("/app/data", owner=(1000, 1000), mode=0o600)
        as_file = reach(ROOT_DIR, APP_DIR, a_file(ledger))
        assert run("path_writable", image(as_file), path="/app/data").passed

    def test_a_missing_path_under_a_file_fails(self) -> None:
        ledger = a_file(a_directory("/app", owner=(1000, 1000)))
        report = run(
            "path_writable",
            image(reach(ROOT_DIR, ledger, exists=False)),
            path="/app/data",
        )
        assert not report.passed

    def test_a_directory_above_it_that_cannot_be_entered_fails(self) -> None:
        sealed = a_directory("/app", mode=0o700, at=2)
        owned = a_directory("/app/data", owner=(1000, 1000))
        report = run(
            "path_writable", image(reach(ROOT_DIR, sealed, owned)), path="/app/data"
        )
        assert not report.passed
        assert (report.actual or "").startswith(
            "'app' (uid 1000) cannot enter /app (0:0, mode 700"
        )

    def test_a_failure_quotes_what_the_grader_could_not_read(self) -> None:
        access = reach(
            ROOT_DIR, APP_DIR, a_directory("/app/data"), notes=("line 5 is opaque",)
        )
        report = run("path_writable", image(access), path="/app/data")
        assert report.actual is not None
        assert report.actual.endswith("from the base image); line 5 is opaque")

    def test_a_build_that_stops_writes_nothing(self) -> None:
        owned = a_directory("/app/data", owner=(1000, 1000))
        access = reach(ROOT_DIR, APP_DIR, owned, stopped="line 7: `chown` fails")
        report = run("path_writable", image(access), path="/app/data")
        assert not report.passed
        assert report.actual == (
            "the build stops before there is an image: line 7: `chown` fails"
        )

    def test_root_can_write_anywhere(self) -> None:
        report = run(
            "path_writable",
            FakeBuildQuery(paths={"/app/data": reach(ROOT_DIR, APP_DIR)}),
            path="/app/data",
        )
        assert report.passed
        assert report.actual == "it runs as 'root', uid 0, who can write anywhere"

    def test_a_user_the_image_does_not_have_cannot_start(self) -> None:
        report = run("path_writable", FakeBuildQuery(user="ghost"), path="/app/data")
        assert not report.passed
        assert report.actual is not None
        assert (report.actual or "").startswith("the image has no user 'ghost'")

    def test_by_asks_about_another_account_and_reads_negated(self) -> None:
        open_to_all = a_directory("/app/data", mode=0o777)
        nobody = an_account("nobody", 65534)
        query = image(reach(ROOT_DIR, APP_DIR, open_to_all), nobody)
        report = run(
            "path_writable", query, negated=True, path="/app/data", by="nobody"
        )
        assert not report.passed
        assert report.expected == "not nobody can write /app/data"

    def test_by_an_account_the_image_lacks_fails(self) -> None:
        report = run("path_writable", image(reach(ROOT_DIR)), path="/x", by="ghost")
        assert report.actual is not None
        assert "no user 'ghost'" in report.actual

    def test_an_unreadable_definition_says_so(self) -> None:
        report = run("path_writable", FakeBuildQuery(error="bad"), path="/app/data")
        assert report.actual == "<no definition could be read>"
