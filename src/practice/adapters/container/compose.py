"""A compose file, read with PyYAML and normalised to compose's long form.

**Normalising is the grading decision, not a convenience.** Compose accepts
several spellings of the same setting:

    environment: [DATABASE_URL=postgres://db/app]
    environment: {DATABASE_URL: postgres://db/app}

    depends_on: [db]
    depends_on: {db: {condition: service_started}}

An assertion written against one spelling would fail a solver who used the
other, which is grading the text. So every service is rewritten into the long
form compose itself resolves to (`docker compose config` prints the same
shape) before an assertion sees it. The five settings rewritten are the five
the exercises read. Anything else passes through as YAML loaded it.

`healthcheck.test` as a bare string becomes `["CMD-SHELL", ...]`, which is
what compose does with it. A pattern of `pg_isready` matches both shapes,
because `render` joins a list with spaces.

**`volumes` came with Phase 23, and every rule in `_volume` was measured**
against `docker compose config` (Compose on Docker Desktop 28.3.3) rather
than read from the specification. Three of them are not obvious. A source
that starts with `.`, `/` or `~`, or a drive letter, is a bind and anything
else names a volume. Compose *ignores* a mode it does not know (`:bogus`
passes `config`), so this does too rather than refusing a file compose runs.
And a named volume the top level does not declare is refused (*refers to
undefined volume*), which matters more than it looks: the obvious way to
write the node_modules fix forgets that block, and a grader that accepted it
would pass a file `compose up` will not start.

One rule is an assumption rather than a measurement: a source that starts
with `$` is a bind. Compose would interpolate it first, and this module reads
no environment; `${PWD}` and `$HOME` are host paths, and a volume *named* by
a variable is rare enough to be the case that gets it wrong.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Final

import yaml

__all__ = ["ComposeError", "parse_compose"]

_DEFAULT_CONDITION: Final = "service_started"
#: A Windows drive letter, which is the one colon a volume source may contain.
_DRIVE: Final = re.compile(r"^[A-Za-z]:[\\/]")
#: A colon that separates source, target and mode: not one inside `${...}`,
#: where `${HOME:-.}` spells a default and splitting there made `${HOME` the
#: source and `-.}/cache` the target.
_VOLUME_SEPARATOR: Final = re.compile(r":(?![^{}]*\})")
#: The short-syntax modes compose turns into fields. Others it drops silently.
_PROPAGATION: Final = frozenset(
    {"shared", "rshared", "slave", "rslave", "private", "rprivate"}
)


class ComposeError(Exception):
    """A compose file that compose would refuse, in a sentence the solver can act on."""


def parse_compose(text: str) -> dict[str, dict[str, object]]:
    """Every service, normalised. Raises `ComposeError`."""
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ComposeError(f"compose.yaml is not valid YAML: {exc}") from exc
    if not isinstance(document, Mapping):
        raise ComposeError("compose.yaml must be a mapping with a `services:` key")
    services = document.get("services")
    if not isinstance(services, Mapping) or not services:
        raise ComposeError("compose.yaml declares no `services:`")

    declared = document.get("volumes")
    volumes = {str(key) for key in declared} if isinstance(declared, Mapping) else set()

    normalised: dict[str, dict[str, object]] = {}
    for name, body in services.items():
        if not isinstance(body, Mapping):
            raise ComposeError(f"service {name!r} must be a mapping of settings")
        service = _service(str(name), body)
        _require_declared(str(name), service, volumes)
        normalised[str(name)] = service
    return normalised


def _service(name: str, body: Mapping[object, object]) -> dict[str, object]:
    service = {str(key): value for key, value in body.items()}
    if "environment" in service:
        service["environment"] = _environment(name, service["environment"])
    if "depends_on" in service:
        service["depends_on"] = _depends_on(name, service["depends_on"])
    if "ports" in service:
        service["ports"] = _ports(name, service["ports"])
    if "volumes" in service:
        service["volumes"] = _volumes(name, service["volumes"])
    healthcheck = service.get("healthcheck")
    if isinstance(healthcheck, Mapping):
        check = {str(key): value for key, value in healthcheck.items()}
        if isinstance(check.get("test"), str):
            check["test"] = ["CMD-SHELL", check["test"]]
        service["healthcheck"] = check
    return service


def _environment(name: str, value: object) -> dict[str, str | None]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(key): _text(item) for key, item in value.items()}
    if isinstance(value, list):
        environment: dict[str, str | None] = {}
        for entry in value:
            key, equals, item = str(entry).partition("=")
            environment[key] = item if equals else None
        return environment
    raise ComposeError(f"service {name!r}: environment must be a list or a mapping")


def _depends_on(name: str, value: object) -> dict[str, dict[str, object]]:
    if isinstance(value, list):
        return {str(item): {"condition": _DEFAULT_CONDITION} for item in value}
    if isinstance(value, Mapping):
        dependencies: dict[str, dict[str, object]] = {}
        for other, settings in value.items():
            long = (
                {str(key): item for key, item in settings.items()}
                if isinstance(settings, Mapping)
                else {}
            )
            long.setdefault("condition", _DEFAULT_CONDITION)
            dependencies[str(other)] = long
        return dependencies
    raise ComposeError(f"service {name!r}: depends_on must be a list or a mapping")


def _ports(name: str, value: object) -> list[object]:
    if not isinstance(value, list):
        raise ComposeError(f"service {name!r}: ports must be a list")
    return [_port(entry) if isinstance(entry, str | int) else entry for entry in value]


def _port(entry: str | int) -> dict[str, object]:
    """`"127.0.0.1:8000:80/udp"` and its shorter forms, as compose's long form."""
    text, _, protocol = str(entry).partition("/")
    parts = text.rsplit(":", 2)
    target = parts.pop()
    published = parts.pop() if parts else None
    host_ip = parts.pop() if parts else None
    port: dict[str, object] = {"target": target, "protocol": protocol or "tcp"}
    if published:
        port["published"] = published
    if host_ip:
        port["host_ip"] = host_ip
    return port


def _volumes(name: str, value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ComposeError(f"service {name!r}: volumes must be a list")
    mounts: list[dict[str, object]] = []
    for entry in value:
        if isinstance(entry, str):
            mounts.append(_volume(name, entry))
        elif isinstance(entry, Mapping):
            mounts.append({str(key): item for key, item in entry.items()})
        else:
            raise ComposeError(
                f"service {name!r}: a volume is a string or a mapping, not {entry!r}"
            )
    return mounts


def _volume(name: str, entry: str) -> dict[str, object]:
    """`.:/app:ro`, `cache:/data`, `/app/node_modules`, as compose's long form.

    The source is kept as written. `docker compose config` resolves `.` to an
    absolute host path, which is the one place the two shapes differ, and no
    assertion should depend on where a workspace happens to live.
    """
    drive = entry[:2] if _DRIVE.match(entry) else ""
    parts = _VOLUME_SEPARATOR.split(entry[len(drive) :])
    parts[0] = drive + parts[0]
    if len(parts) > 3:  # noqa: PLR2004 - source, target and mode
        raise ComposeError(
            f"service {name!r}: invalid volume {entry!r}: too many colons"
        )
    if len(parts) == 1:
        return {"type": "volume", "target": _target(parts[0])}

    source, target, *modes = parts
    # Compose interpolates before it classifies, and this does not
    # interpolate at all, so a source that opens with a variable is taken as
    # the host path it almost always is: `${PWD}:/app` read as a named volume
    # was then refused as undeclared, failing a file `compose up` starts.
    bind = source.startswith((".", "/", "~", "$")) or bool(drive)
    mount: dict[str, object] = {
        "type": "bind" if bind else "volume",
        "source": source,
        "target": _target(target),
    }
    options: dict[str, object] = {}
    for mode in modes[0].split(",") if modes else ():
        if mode == "ro":
            mount["read_only"] = True
        elif mode in {"z", "Z"}:
            options["selinux"] = mode
        elif mode in _PROPAGATION:
            options["propagation"] = mode
        elif mode == "nocopy":
            options["nocopy"] = True
    if options:
        mount["bind" if bind else "volume"] = options
    return mount


def _target(path: str) -> str:
    return path.rstrip("/") or "/"


def _require_declared(
    name: str, service: Mapping[str, object], declared: set[str]
) -> None:
    """A named volume must appear under the top-level `volumes:`, as compose insists."""
    mounts = service.get("volumes")
    for mount in mounts if isinstance(mounts, list) else ():
        source = mount.get("source")
        named = mount.get("type") == "volume" and source is not None
        if named and str(source) not in declared:
            raise ComposeError(
                f"service {name!r} refers to undefined volume {source}: "
                f"declare it under a top-level `volumes:` key"
            )


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
