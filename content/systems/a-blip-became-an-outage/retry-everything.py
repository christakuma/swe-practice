"""Counter-example: the right waits, for every kind of failure."""


class Unavailable(Exception):
    """The database could not be reached. The call did not happen."""


ATTEMPTS = 4


def call_with_retries(operation, *, sleep, rng):
    for attempt in range(1, ATTEMPTS):
        try:
            return operation()
        except Exception:
            sleep(rng.uniform(0, 0.1 * 2**attempt))
    return operation()
