"""Who owns what after a Dockerfile, read by `ParsedBuildQuery`. Every case is measured.

Each expectation here was read off a real BuildKit build (Docker 28.3,
`python:3.12-slim`, Debian 13) with `stat -c '%U:%G %a'`, and the docstring of
`adapters/container/filesystem.py` names the four that surprised. The case
worth reading first is `test_copy_chown_leaves_an_existing_destination_to_root`:
it is the wrong answer that looks most like a right one, and a check that
grepped for `--chown` would pass it.
"""

from __future__ import annotations

import pytest

from practice.adapters.container import ParsedBuildQuery
from practice.domain.ports import Account

CONTEXT = {"app.py": "", "sub/f.txt": ""}
SLIM = "FROM python:3.12-slim\n"


def query(body: str, *, base: str = SLIM) -> ParsedBuildQuery:
    return ParsedBuildQuery(context=CONTEXT, editable="Dockerfile", source=base + body)


def owners(body: str, *paths: str, base: str = SLIM) -> list[str]:
    """`stat -c '%U:%G %a'` for each path, as the model has it."""
    q = query(body, base=base)
    found = []
    for path in paths:
        access = q.path_access(path)
        assert access.exists, f"{path} is not in the image"
        entry = access.chain[-1]
        found.append(f"{entry.owner} {entry.mode:o}")
    return found


class TestWorkdir:
    def test_makes_every_missing_directory_as_the_user_in_force(self) -> None:
        body = "RUN useradd -m app\nUSER app\nWORKDIR /srv/a/b\n"
        assert owners(body, "/srv", "/srv/a", "/srv/a/b") == [
            "root:root 755",
            "app:app 755",
            "app:app 755",
        ]

    def test_leaves_an_existing_directory_alone(self) -> None:
        body = "RUN useradd -m app && mkdir -p /pre/data\nUSER app\nWORKDIR /pre/data\n"
        assert owners(body, "/pre/data") == ["root:root 755"]

    def test_a_bare_uid_owns_with_the_same_number(self) -> None:
        assert owners("USER 4242\nWORKDIR /z\n", "/z") == ["4242:4242 755"]

    def test_a_user_the_image_lacks_leaves_it_to_root(self) -> None:
        assert owners("USER ghost\nWORKDIR /x\n", "/x") == ["root:root 755"]


class TestCopy:
    def test_ignores_user(self) -> None:
        body = "RUN useradd app\nUSER app\nCOPY . /asuser/\n"
        assert (
            owners(body, "/asuser", "/asuser/app.py", "/asuser/sub")
            == ["root:root 755"] * 3
        )

    def test_chown_creates_every_missing_parent_as_that_user(self) -> None:
        body = "RUN useradd -m app\nCOPY --chown=app:app . /new/dest/\n"
        assert (
            owners(body, "/new", "/new/dest", "/new/dest/sub/f.txt")
            == ["app:app 755"] * 3
        )

    def test_one_file_copied_to_the_workdir_lands_inside_it(self) -> None:
        """`COPY app.py .` writes `/app/app.py`; the `WORKDIR` stays a directory.

        The landing rule once knew only a trailing slash and several sources,
        so this landed the file *at* `/app`, and the ownership model replaced
        the user's directory with a root-owned file.
        """
        body = "RUN useradd -m app\nUSER app\nWORKDIR /app\nCOPY app.py .\n"
        assert owners(body, "/app", "/app/app.py") == [
            "app:app 755",
            "root:root 755",
        ]

    def test_one_file_copied_from_a_stage_to_the_workdir_lands_inside_it(
        self,
    ) -> None:
        body = (
            "WORKDIR /src\nCOPY app.py .\n"
            "FROM python:3.12-slim\nWORKDIR /app\nCOPY --from=0 /src/app.py .\n"
        )
        assert query(body).path_access("/app/app.py").exists

    def test_copy_chown_leaves_an_existing_destination_to_root(self) -> None:
        body = "RUN useradd -m app\nWORKDIR /exist\nCOPY --chown=app:app . .\n"
        assert owners(body, "/exist", "/exist/app.py", "/exist/sub") == [
            "root:root 755",
            "app:app 755",
            "app:app 755",
        ]

    def test_chown_with_a_name_alone_takes_the_users_own_group(self) -> None:
        body = "RUN useradd -N nogrp\nCOPY --chown=nogrp . /c1/\n"
        assert owners(body, "/c1/app.py") == ["nogrp:users 755"]

    def test_chown_with_numbers_the_image_lacks(self) -> None:
        body = "COPY --chown=1234:5678 app.py /r/s/t.txt\n"
        assert owners(body, "/r", "/r/s/t.txt") == ["1234:5678 755"] * 2

    def test_chmod_applies_to_the_directories_it_creates_under_the_umask(
        self,
    ) -> None:
        assert owners("COPY --chmod=750 app.py /p/q/\n", "/p", "/p/q/app.py") == [
            "root:root 750",
            "root:root 750",
        ]
        assert owners("COPY --chmod=777 app.py /chm/\n", "/chm") == ["root:root 755"]

    def test_an_unreadable_chmod_is_a_note_and_not_a_guess(self) -> None:
        access = query("COPY --chmod=u+rwx app.py /p/\n").path_access("/p")
        assert access.notes == (
            "line 2: the grader cannot read `--chmod=u+rwx`, so it was not applied",
        )

    def test_a_chown_naming_nobody_the_image_has_stops_the_build(self) -> None:
        access = query("COPY --chown=ghost . /x/\n").path_access("/x")
        assert access.stopped == (
            "line 2: --chown=ghost names an account the image does not have"
        )

    def test_add_from_a_url_is_not_followed(self) -> None:
        assert not query("ADD https://example.com/a.tgz /a/\n").path_access("/a").exists


class TestCopyFrom:
    BUILD = (
        "FROM python:3.12-slim AS build\n"
        "RUN useradd -N nogrp && useradd -m app && mkdir /out "
        "&& chown app:app /out && chmod 700 /out\n"
        "COPY --chown=nogrp . /c1/\n"
        "FROM python:3.12-slim\n"
    )

    def test_a_directory_lands_in_one_root_creates(self) -> None:
        """Measured: `/c1` was `nogrp:users` in the builder; `/from/c1` is root's."""
        body = "COPY --from=build /out /from/out\n"
        assert owners(body, "/from", "/from/out", base=self.BUILD) == [
            "root:root 755",
            "root:root 755",
        ]

    def test_the_directory_it_copies_into_is_root_s_and_its_contents_are_kept(
        self,
    ) -> None:
        body = "COPY --from=build /c1 /from/c1\n"
        assert owners(body, "/from/c1", "/from/c1/app.py", base=self.BUILD) == [
            "root:root 755",
            "1000:users 755",
        ]

    def test_chown_overrides_what_it_keeps(self) -> None:
        body = "RUN useradd svc\nCOPY --from=build --chown=svc /c1 /c2\n"
        assert owners(body, "/c2", "/c2/sub/f.txt", base=self.BUILD) == [
            "svc:svc 755",
            "svc:svc 755",
        ]

    def test_chmod_overrides_the_mode(self) -> None:
        body = "COPY --from=build --chmod=640 /c1/app.py /one\n"
        assert owners(body, "/one", base=self.BUILD) == ["1000:users 640"]

    def test_what_a_build_made_lands_as_a_directory_its_chown_owns(self) -> None:
        """Calling it a file would fail `app` creating `/app/data` inside it."""
        body = "RUN useradd app\nCOPY --from=build --chown=app /src/dist /app\n"
        q = query(body + "USER app\n", base=self.BUILD)
        assert owners(body, "/app", base=self.BUILD) == ["app:app 755"]
        assert q.path_access("/app").chain[-1].directory

    def test_the_root_of_a_stage_keeps_every_name(self) -> None:
        """`COPY --from=build / /rootfs` once landed `/out` at `/rootfs/ut`:
        the relative path was cut one character past a separator `/` lacks."""
        q = query("COPY --from=build / /rootfs\n", base=self.BUILD)
        assert q.path_access("/rootfs/out").exists
        assert not q.path_access("/rootfs/ut").exists
        assert owners(
            "COPY --from=build / /rootfs\n", "/rootfs/c1/app.py", base=self.BUILD
        ) == ["1000:users 755"]

    def test_from_another_image_is_root_s(self) -> None:
        body = "COPY --from=nginx:1.27 /etc/nginx/nginx.conf /conf\n"
        assert owners(body, "/conf") == ["root:root 755"]

    def test_a_file_from_an_earlier_stage_keeps_its_owner(self) -> None:
        base = (
            "FROM python:3.12-slim AS build\n"
            "COPY --chown=10:10 app.py /a.py\n"
            "FROM scratch\n"
        )
        assert owners("COPY --from=build /a.py /b/\n", "/b/a.py", base=base) == [
            "10:10 755"
        ]


class TestRun:
    def test_mkdir_p_and_m_set_only_the_last_directory(self) -> None:
        assert owners("RUN mkdir -p -m 777 /m/a/b\n", "/m", "/m/a/b") == [
            "root:root 755",
            "root:root 777",
        ]
        assert owners("RUN mkdir -pm 700 /n\n", "/n") == ["root:root 700"]

    def test_install_d_sets_owner_and_mode_and_leaves_parents_to_the_builder(
        self,
    ) -> None:
        body = (
            "RUN adduser --disabled-password --gecos '' ad1 "
            "&& install -d -o ad1 -g ad1 /i/x && install -d -m 700 /i/y "
            "&& install -d --owner=ad1 /i/z\n"
        )
        assert owners(body, "/i", "/i/x", "/i/y", "/i/z") == [
            "root:root 755",
            "ad1:ad1 755",
            "root:root 700",
            "ad1:root 755",
        ]

    def test_chown_spellings(self) -> None:
        body = (
            "RUN adduser --disabled-password --gecos '' ad1 "
            "&& mkdir /c1 /c2 /c3 /c4 /c5 && chown ad1 /c1 && chown ad1: /c2 "
            "&& chown :ad1 /c3 && chown ad1.ad1 /c4 && chown 1000:1000 /c5 "
            "&& chgrp users /c1\n"
        )
        assert owners(body, "/c1", "/c2", "/c3", "/c4", "/c5") == [
            "ad1:users 755",
            "ad1:ad1 755",
            "root:ad1 755",
            "ad1:ad1 755",
            "ad1:ad1 755",
        ]

    @pytest.mark.parametrize(
        ("mode", "result"),
        [
            ("+w,o+w", "757"),
            ("a=rwx,g-w", "757"),
            ("1777", "1777"),
            ("u=rwx,go=", "700"),
            ("o+t", "1755"),
            ("g+s", "2755"),
            ("a-x,u+X", "744"),
            ("=r", "444"),
        ],
    )
    def test_chmod(self, mode: str, result: str) -> None:
        assert owners(f"RUN mkdir /c && chmod {mode} /c\n", "/c") == [
            f"root:root {result}"
        ]

    def test_chmod_r_reaches_everything_below(self) -> None:
        body = "COPY . /app/\nRUN chmod -R go-rx /app && chown -R 7:7 /app\n"
        assert owners(body, "/app", "/app/sub/f.txt") == ["lp:lp 700"] * 2

    def test_chmod_of_a_path_the_model_never_saw_assumes_a_base_directory(
        self,
    ) -> None:
        assert owners("RUN chmod 1777 /var/cache/app\n", "/var/cache/app") == [
            "root:root 1777"
        ]

    def test_x_capital_adds_search_to_a_file_only_if_it_had_some(self) -> None:
        body = "COPY --chmod=644 app.py /a.py\nRUN chmod a+X /a.py\n"
        assert owners(body, "/a.py") == ["root:root 644"]

    def test_rm_takes_a_path_and_everything_below_it(self) -> None:
        q = query("COPY . /app/\nRUN rm -rf /app/sub\n")
        assert not q.path_access("/app/sub/f.txt").exists
        assert q.path_access("/app/app.py").exists

    def test_rm_rf_root_leaves_the_root(self) -> None:
        q = query("COPY . /app/\nRUN rm -rf /\n")
        assert [entry.path for entry in q.path_access("/app").chain] == ["/"]

    def test_exec_form_is_read_too(self) -> None:
        assert owners('RUN ["mkdir", "-m", "700", "/e"]\n', "/e") == ["root:root 700"]

    def test_variables_are_the_shells(self) -> None:
        body = (
            "ARG UID=10001\nENV DATA=/data\n"
            "RUN useradd -u $UID app && mkdir $DATA && chown ${UID} $DATA\n"
        )
        assert owners(body, "/data") == ["app:root 755"]

    def test_a_leading_assignment_is_not_the_command(self) -> None:
        assert owners("RUN DEBIAN_FRONTEND=x mkdir /f\n", "/f") == ["root:root 755"]

    def test_a_pipe_and_an_or_are_not_followed(self) -> None:
        q = query("RUN echo x | mkdir /p1 || mkdir /p2\n")
        assert not q.path_access("/p2").exists

    def test_what_follows_a_double_dash_is_operands(self) -> None:
        assert owners("RUN mkdir -- -odd\n", "/-odd") == ["root:root 755"]

    def test_commands_it_does_not_watch_change_nothing(self) -> None:
        assert not query("RUN pip install flask && touch /t\n").path_access("/t").exists

    def test_an_unbalanced_quote_is_skipped(self) -> None:
        assert not query("RUN mkdir '/q\n").path_access("/q").exists

    def test_install_without_d_installs_a_file_and_is_not_followed(self) -> None:
        assert (
            not query("RUN install -m 755 a /usr/local/bin/a\n")
            .path_access("/usr/local/bin/a")
            .exists
        )

    def test_cd_moves_the_rest_of_the_line(self) -> None:
        """Not followed, `cd /app && mkdir data` made `/data`, and a correct
        `chown app data` after it gave `app` the wrong directory."""
        q = query("RUN mkdir /app && cd /app && mkdir data && chown 7 data\n")
        assert owners("RUN mkdir /app && cd /app && mkdir data\n", "/app/data") == [
            "root:root 755"
        ]
        assert q.path_access("/app/data").chain[-1].uid == 7
        assert not q.path_access("/data").exists

    def test_cd_ends_with_its_line(self) -> None:
        q = query("RUN mkdir /app && cd /app\nRUN mkdir data\n")
        assert q.path_access("/data").exists
        assert not q.path_access("/app/data").exists

    @pytest.mark.parametrize("command", ["cd", "cd -", "cd ~/x"])
    def test_a_cd_that_depends_on_the_shell_is_a_note(self, command: str) -> None:
        access = query(f"RUN {command} && mkdir d\n").path_access("/d")
        assert access.exists
        assert "cannot follow" in access.notes[0]

    @pytest.mark.parametrize(
        "redirect",
        ["2>/dev/null", "> /dev/null", ">/dev/null 2>&1", "&> log", ">& log"],
    )
    def test_a_redirection_is_not_an_operand(self, redirect: str) -> None:
        """`mkdir /r 2>/dev/null`, run from `/`, also asked for `/2>/dev/null`,
        whose parent `/2>` does not exist, and stopped a build that runs."""
        q = query(f"RUN mkdir /r {redirect}\n")
        assert q.path_access("/r").exists
        assert q.path_access("/r").stopped is None
        for target in ("/dev/null", "/log", "/2>", "/>", "/&>"):
            assert not q.path_access(target).exists, target

    def test_a_command_substitution_is_a_note(self) -> None:
        access = query("RUN mkdir /d && chown $(id -u nobody) /d\n").path_access("/d")
        assert access.notes == (
            (
                "line 2 runs chown with a command substitution, which the grader "
                "cannot evaluate"
            ),
        )

    @pytest.mark.parametrize(
        "command", ["chmod g=u /d", "mkdir -m g=u /e", "install -d -m u=rwx,g=u /e"]
    )
    def test_a_mode_copying_bits_is_a_note(self, command: str) -> None:
        access = query(f"RUN mkdir /d && {command}\n").path_access("/d")
        assert access.notes
        assert "the grader cannot read" in access.notes[0]


class TestAStageBuiltOnAnother:
    """What a `FROM <stage>` inherits: its `WORKDIR` and `ENV`, not its `ARG`.

    Docker's documented behaviour rather than a measurement, and the layer
    model in `build_query.py` already inherited the workdir: this model reset
    both per stage, so the two disagreed about where the same line wrote.
    """

    BASE = (
        "FROM python:3.12-slim AS base\n"
        "RUN useradd -m app\n"
        "WORKDIR /app\n"
        "ENV APP_USER=app\n"
        "ARG DIR=/a\n"
        "FROM base\n"
    )

    def test_the_workdir_carries_over(self) -> None:
        q = query("RUN mkdir data\nCOPY app.py .\n", base=self.BASE)
        assert q.path_access("/app/data").exists
        assert q.path_access("/app/app.py").exists
        assert not q.path_access("/data").exists

    def test_env_carries_over(self) -> None:
        body = "USER $APP_USER\nWORKDIR /w\nRUN mkdir /w/x\n"
        access = query(body, base=self.BASE).path_access("/w/x")
        assert access.stopped is None
        assert owners(body, "/w", base=self.BASE) == ["app:app 755"]

    def test_the_user_it_runs_as_is_the_same_user_in_both_models(self) -> None:
        """`lineage` dropped inherited `ENV`: `final_user` was `''` while the
        ownership model ran this image as `app`, in one verdict."""
        q = query("USER $APP_USER\n", base=self.BASE)
        account = q.account()
        assert account is not None
        assert q.final_user() == account.name == "app"

    def test_a_workdir_from_env_is_where_the_layer_model_puts_files(self) -> None:
        """Joined literally, `WORKDIR $D` put the builder's files under `/$D`,
        the copy of `/app/.env` found nothing, and `.env` was said not to
        ship."""
        source = (
            "FROM python:3.12-slim AS build\nENV D=/app\nWORKDIR $D\nCOPY . .\n"
            "FROM python:3.12-slim\nCOPY --from=build /app/.env /x\n"
        )
        q = ParsedBuildQuery(
            context={".env": "", "app.py": ""}, editable="Dockerfile", source=source
        )
        assert q.path_in_image(".env")
        assert q.path_access("/x").exists

    def test_arg_does_not(self) -> None:
        assert query("RUN mkdir /x$DIR\n", base=self.BASE).path_access("/x").exists


class TestRunAsAnotherUser:
    """Measured: each of these stops the build."""

    APP = "RUN useradd -m app && mkdir /owned && chown app /owned\nUSER app\n"

    @pytest.mark.parametrize(
        ("command", "reason"),
        [
            ("mkdir /app", "app cannot write /"),
            ("chown app /etc", "changing ownership of /etc: Operation not permitted"),
            (
                "chown root /owned",
                "changing ownership of /owned: Operation not permitted",
            ),
            ("chmod 777 /etc", "changing permissions of /etc: Operation not permitted"),
            ("install -d -o app /owned/x", "Operation not permitted"),
            ("useradd other", "only root can change the image's accounts"),
            ("mkdir /etc", "cannot create /etc: File exists"),
            ("mkdir /a/b", "cannot create /a/b: No such file or directory"),
        ],
    )
    def test_a_command_it_may_not_run(self, command: str, reason: str) -> None:
        access = query(f"{self.APP}RUN {command}\n").path_access("/owned")
        assert access.stopped == f"line 4: `{command}` fails: {reason}"

    def test_what_it_owns_it_may_change(self) -> None:
        body = (
            f"{self.APP}"
            "RUN mkdir -p /owned/a/b && chmod 700 /owned && chgrp app /owned\n"
        )
        assert owners(body, "/owned", "/owned/a/b") == ["app:app 700", "app:app 755"]

    def test_a_guarded_failure_is_carried_on_past(self) -> None:
        q = query(f"{self.APP}RUN mkdir /x || true\nRUN mkdir /owned/y\n")
        assert q.path_access("/owned").stopped is None
        assert q.path_access("/owned/y").exists

    def test_nothing_after_a_stop_is_applied(self) -> None:
        body = f"{self.APP}RUN chown app /etc\nUSER root\nRUN mkdir /later\n"
        assert not query(body).path_access("/later").exists

    def test_a_user_the_image_lacks_stops_the_next_run(self) -> None:
        access = query("USER ghost\nRUN true\n").path_access("/")
        assert access.stopped == (
            "line 3 runs as 'ghost', and the image has no such user: unable to "
            "find user"
        )

    def test_root_s_run_never_stops(self) -> None:
        assert query("RUN mkdir -p /etc\n").path_access("/etc").stopped is None


class TestAccounts:
    """Debian's allocators, measured in one `RUN` on `python:3.12-slim`."""

    BODY = (
        "RUN useradd -u 10001 a && adduser --disabled-password --gecos '' b "
        "&& useradd c && groupadd g1 && groupadd -r g2 && addgroup g3 "
        "&& addgroup --system g4 && groupadd g5 -g 2000 && useradd d "
        "&& useradd -r e && adduser --system f && useradd -g g1 -G staff,users h "
        "&& useradd -m -d /srv/home/i i && usermod -aG g1 c "
        "&& adduser --system --group svc && addgroup c g5\n"
    )

    @pytest.mark.parametrize(
        ("user", "uid", "gids"),
        [
            ("a", 10001, {10001}),
            ("b", 1000, {1000, 100}),
            ("c", 10002, {10002, 10003, 2000}),
            ("d", 10003, {10004}),
            ("e", 999, {998}),
            ("f", 100, {65534}),
            ("h", 10004, {10003, 50, 100}),
            ("svc", 101, {102}),
        ],
    )
    def test_ids_are_allocated_as_debian_allocates_them(
        self, user: str, uid: int, gids: set[int]
    ) -> None:
        assert query(self.BODY).account(user) == Account(
            name=user, uid=uid, gids=frozenset(gids)
        )

    def test_a_home_is_the_users_and_700_and_its_parents_are_root_s(self) -> None:
        assert owners(self.BODY, "/srv/home", "/srv/home/i") == [
            "root:root 755",
            "i:i 700",
        ]

    @pytest.mark.parametrize(
        ("spec", "expected"),
        [
            ("b", Account(name="b", uid=1000, gids=frozenset({1000, 100}))),
            ("1000", Account(name="1000", uid=1000, gids=frozenset({1000, 100}))),
            ("b:users", Account(name="b", uid=1000, gids=frozenset({100}))),
            ("1000:1000", Account(name="1000", uid=1000, gids=frozenset({1000}))),
            ("4242", Account(name="4242", uid=4242, gids=frozenset({0}))),
            ("b:4242", Account(name="b", uid=1000, gids=frozenset({4242}))),
            ("ghost", None),
            ("b:ghosts", None),
        ],
    )
    def test_a_user_value_runs_as_docker_run_measured(
        self, spec: str, expected: Account | None
    ) -> None:
        assert query(self.BODY).account(spec) == expected

    def test_the_final_user_by_default(self) -> None:
        assert query("USER nobody\n").account() == Account(
            name="nobody", uid=65534, gids=frozenset({65534})
        )

    @pytest.mark.parametrize(
        ("command", "reason"),
        [
            ("useradd root", "user 'root' already exists"),
            ("useradd users", "group users exists"),
            ("useradd -g ghosts x", "group 'ghosts' does not exist"),
            ("useradd -G ghosts x", "group 'ghosts' does not exist"),
            ("groupadd users", "group 'users' already exists"),
            ("usermod -aG users ghost", "user 'ghost' does not exist"),
            ("chown ghost /tmp", "invalid user or group 'ghost'"),
            ("chgrp ghosts /tmp", "invalid user or group ':ghosts'"),
            ("install -d -o ghost /x", "invalid user or group 'ghost'"),
        ],
    )
    def test_a_command_debian_refuses(self, command: str, reason: str) -> None:
        access = query(f"RUN {command}\n").path_access("/")
        assert access.stopped == f"line 2: `{command}` fails: {reason}"

    def test_usermod_without_append_replaces_the_groups(self) -> None:
        body = "RUN useradd -G staff x && usermod -G users x && usermod x\n"
        assert query(body).account("x") == Account(
            name="x", uid=1000, gids=frozenset({1000, 100})
        )

    def test_scratch_has_no_accounts_and_only_a_root_directory(self) -> None:
        q = query("COPY app.py /app\n", base="FROM scratch\n")
        assert q.account() is None
        assert q.account("65532") == Account(
            name="65532", uid=65532, gids=frozenset({0})
        )
        assert [entry.path for entry in q.path_access("/app").chain] == ["/", "/app"]

    def test_accounts_and_paths_follow_a_stage_built_from_another(self) -> None:
        base = (
            "FROM python:3.12-slim AS base\n"
            "RUN useradd app && mkdir /d && chown app /d\n"
            "FROM base\n"
        )
        q = query("USER app\n", base=base)
        assert q.account() is not None
        assert owners("", "/d", base=base) == ["app:root 755"]

    def test_empty_commands_change_nothing(self) -> None:
        q = query("RUN useradd && adduser && groupadd && addgroup && usermod -aG x\n")
        assert q.path_access("/").stopped is None


class TestThePort:
    def test_a_path_the_image_lacks_ends_at_its_deepest_ancestor(self) -> None:
        access = query("WORKDIR /app\n").path_access("/app/data/")
        assert not access.exists
        assert [entry.path for entry in access.chain] == ["/", "/app"]

    def test_an_unclosed_quote_is_the_definition_s_error_not_a_crash(self) -> None:
        """Raised from `ParsedBuildQuery`'s constructor, it took the whole
        grading pass down instead of failing every check with the reason."""
        q = query('ENV A="x\nRUN useradd app\n')
        assert q.error() == "line 2: No closing quotation"
        assert q.stages() == ()

    @pytest.mark.parametrize(
        "body",
        [
            "USER \N{SUPERSCRIPT TWO}\n",
            "RUN useradd -u \N{SUPERSCRIPT TWO} app\n",
            "RUN mkdir /d && chown 1:\N{SUPERSCRIPT TWO} /d\n",
            f"USER {'1' * 5000}\n",
        ],
    )
    def test_an_id_int_would_refuse_is_not_a_crash(self, body: str) -> None:
        """`str.isdigit` is true of all four and `int` raised on each, from
        the constructor. `USER` with one is a user the image does not have."""
        q = query(body)
        if body.startswith("USER"):
            assert q.account() is None
        assert q.error() is None

    def test_a_definition_with_no_stages_reads_as_scratch(self) -> None:
        q = ParsedBuildQuery(
            context={}, editable="compose.yaml", source="services: {}\n"
        )
        assert q.path_access("/x").chain[-1].path == "/"
        assert q.account() is None
