""".dockerignore matching, and compose's spellings normalised to one."""

from __future__ import annotations

import pytest

from practice.adapters.container.compose import ComposeError, parse_compose
from practice.adapters.container.dockerignore import IgnoreRules


class TestDockerignore:
    @pytest.mark.parametrize(
        ("rules", "path", "excluded"),
        [
            ("node_modules", "node_modules/a/b.js", True),
            ("*.env", ".env", True),
            ("*.env", "config/.env", False),
            ("**/*.env", "config/.env", True),
            ("**/*.env", ".env", True),
            ("*.md\n!README.md", "README.md", False),
            ("*.md\n!README.md", "NOTES.md", True),
            ("!README.md\n*.md", "README.md", True),
            ("/build", "build/out.o", True),
            ("./build/", "build/out.o", True),
            ("# .env\n", ".env", False),
            ("file[0-9].txt", "file3.txt", True),
            ("file[^0-9].txt", "file3.txt", False),
            ("file[.txt", "file[.txt", True),
            ("?.py", "a.py", True),
            ("?.py", "ab.py", False),
        ],
    )
    def test_matching(self, rules: str, path: str, excluded: bool) -> None:
        assert IgnoreRules(rules).excludes(path) is excluded

    def test_kept_keeps_order(self) -> None:
        assert IgnoreRules(".env").kept(["b", ".env", "a"]) == ("b", "a")


class TestCompose:
    def test_a_list_environment_becomes_a_mapping(self) -> None:
        services = parse_compose(
            "services:\n  api:\n    environment:\n      - A=1\n      - B\n"
        )
        assert services["api"]["environment"] == {"A": "1", "B": None}

    def test_mapping_values_become_text(self) -> None:
        services = parse_compose(
            "services:\n  api:\n    environment:\n"
            "      PORT: 8000\n      DEBUG: false\n      EMPTY:\n"
        )
        assert services["api"]["environment"] == {
            "PORT": "8000",
            "DEBUG": "false",
            "EMPTY": None,
        }

    def test_short_depends_on_is_service_started(self) -> None:
        services = parse_compose("services:\n  api:\n    depends_on: [db]\n  db: {}\n")
        assert services["api"]["depends_on"] == {"db": {"condition": "service_started"}}

    def test_long_depends_on_keeps_its_condition(self) -> None:
        services = parse_compose(
            "services:\n  api:\n    depends_on:\n"
            "      db: {condition: service_healthy}\n      cache:\n"
        )
        assert services["api"]["depends_on"] == {
            "db": {"condition": "service_healthy"},
            "cache": {"condition": "service_started"},
        }

    def test_a_string_healthcheck_is_cmd_shell(self) -> None:
        services = parse_compose(
            "services:\n  db:\n    healthcheck:\n      test: pg_isready\n"
        )
        assert services["db"]["healthcheck"] == {"test": ["CMD-SHELL", "pg_isready"]}

    @pytest.mark.parametrize(
        ("short", "long"),
        [
            ("8000", {"target": "8000", "protocol": "tcp"}),
            ("8000:80", {"target": "80", "published": "8000", "protocol": "tcp"}),
            (
                "127.0.0.1:8000:80/udp",
                {
                    "target": "80",
                    "published": "8000",
                    "host_ip": "127.0.0.1",
                    "protocol": "udp",
                },
            ),
        ],
    )
    def test_short_ports_become_long(self, short: str, long: dict[str, str]) -> None:
        services = parse_compose(f'services:\n  api:\n    ports: ["{short}"]\n')
        assert services["api"]["ports"] == [long]

    def test_long_ports_pass_through(self) -> None:
        services = parse_compose(
            "services:\n  api:\n    ports:\n      - {target: 80, published: 8000}\n"
        )
        assert services["api"]["ports"] == [{"target": 80, "published": 8000}]

    def test_a_null_environment_is_empty(self) -> None:
        services = parse_compose("services:\n  api:\n    environment:\n")
        assert services["api"]["environment"] == {}

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("services: [\n", "not valid YAML"),
            ("- a\n", "must be a mapping"),
            ("version: '3'\n", "declares no `services:`"),
            ("services:\n  api: 3\n", "must be a mapping of settings"),
            ("services:\n  api:\n    environment: 3\n", "environment must be"),
            ("services:\n  api:\n    depends_on: 3\n", "depends_on must be"),
            ("services:\n  api:\n    ports: 8000\n", "ports must be a list"),
        ],
    )
    def test_refusals(self, text: str, message: str) -> None:
        with pytest.raises(ComposeError, match=message):
            parse_compose(text)
