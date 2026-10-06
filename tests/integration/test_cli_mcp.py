"""`practice mcp`, as far as a test can take a command whose stdout is a protocol.

Two things, and neither is the server's behaviour -- that is
`test_mcp_server.py`'s, and the journey over real stdio is `tests/e2e/`'s.

The first is the refusal. The SDK is an optional extra, so on a base install
this is the one command that cannot run, and what it says then is the whole of
its interface: it has to name the fix, on stderr, and not take the rest of the
CLI down with it. The second is that the extra really is optional -- that
nothing else in the CLI imports the SDK on the way to doing its own job.
"""

from __future__ import annotations

import ast
import inspect
import sys
from typing import TYPE_CHECKING

from typer.testing import CliRunner

import practice.interface.cli.main as cli

if TYPE_CHECKING:
    from collections.abc import Sequence
    from importlib.machinery import ModuleSpec
    from types import ModuleType

    import pytest

runner = CliRunner()


class NoSdk:
    """A meta path finder for which the SDK is not installed.

    The faithful way to stage a base install. The first draft put `None` in
    `sys.modules["mcp"]`, which is the usual trick and is subtly not the same
    failure: `from mcp.server import ...` then raises *"No module named
    'mcp.server'; 'mcp' is not a package"*, naming the submodule, where a
    machine without the package raises *"No module named 'mcp'"*. The command
    decides what to say from that name, and the first version compared it to
    `"mcp"` exactly -- so the usual trick failed the test for a reason no user
    could cause, and passing it would have meant fitting the code to the mock.
    """

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        del path, target
        if fullname.split(".", maxsplit=1)[0] in {"mcp", "mcp_types"}:
            raise ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
        return None


def without_the_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Uninstall the SDK for one test, as far as the import system can tell.

    Everything already imported has to go as well as the finder going in:
    `import` answers from `sys.modules` first, so the SDK's cached modules and
    this project's own adapter over them would be handed straight back and
    nothing would ever reach the finder.
    """
    for name in list(sys.modules):
        if name.split(".")[0] in {"mcp", "mcp_types"} or name.startswith(
            "practice.interface.mcp"
        ):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "meta_path", [NoSdk(), *sys.meta_path])


def test_without_the_extra_it_refuses_and_names_the_fix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    without_the_sdk(monkeypatch)

    result = runner.invoke(cli.app, ["mcp"])

    assert result.exit_code == 2
    assert "uv sync --extra mcp" in result.stderr
    # Nothing on stdout, which is the protocol's: a client that started this
    # must not be handed a sentence where it expected JSON-RPC.
    assert result.stdout == ""


def test_without_the_extra_every_other_command_still_loads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What "optional" has to mean. `practice validate` runs in CI on an
    install that may not have asked for the extra, and a top-level import of
    the SDK anywhere on its path would fail it for want of a package it never
    uses.
    """
    without_the_sdk(monkeypatch)

    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "validate" in result.stdout
    assert "mcp" in result.stdout


def test_a_different_missing_module_is_not_mistaken_for_the_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the SDK's absence is turned into an instruction. Any other import
    failing inside the adapter is a bug in this project, and telling the user
    to install an extra they already have would send them looking for the
    wrong problem.
    """

    class Broken:
        def find_spec(
            self,
            fullname: str,
            path: Sequence[str] | None = None,
            target: ModuleType | None = None,
        ) -> ModuleSpec | None:
            del path, target
            if fullname == "practice.interface.mcp":
                raise ModuleNotFoundError("No module named 'yaml'", name="yaml")
            return None

    for name in list(sys.modules):
        if name.startswith("practice.interface.mcp"):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "meta_path", [Broken(), *sys.meta_path])

    result = runner.invoke(cli.app, ["mcp"])

    assert result.exit_code == 1
    assert isinstance(result.exception, ModuleNotFoundError)
    assert result.exception.name == "yaml"
    assert "uv sync --extra mcp" not in result.stderr


def test_the_cli_module_imports_the_adapter_only_inside_the_command() -> None:
    """The structural half, which cannot be fooled by the order tests ran in:
    `main.py` has no top-level import of the SDK or of this project's adapter
    over it, and the one import there is sits inside `mcp`.
    """
    tree = ast.parse(inspect.getsource(cli))
    top_level = [
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ] + [
        alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    ]

    assert not [name for name in top_level if name.startswith("practice.interface.mcp")]
    assert not [name for name in top_level if name.split(".")[0] == "mcp"]
    assert "from practice.interface.mcp import build_server" in inspect.getsource(
        cli.mcp
    )
