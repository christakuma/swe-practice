from app import app


def test_health_says_ok() -> None:
    seen: dict[str, str] = {}

    def start_response(status: str, _headers: list[tuple[str, str]]) -> None:
        seen["status"] = status

    body = b"".join(app({"PATH_INFO": "/health"}, start_response))
    assert seen["status"] == "200 OK"
    assert body == b"ok\n"
