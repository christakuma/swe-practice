"""Counter-example: exponential backoff, the same for every client."""


class Unavailable(Exception):
    """The database could not be reached. The call did not happen."""


ATTEMPTS = 4


def call_with_retries(operation, *, sleep, rng):
    del rng  # the mistake: every client waits exactly as long as every other
    for attempt in range(1, ATTEMPTS):
        try:
            return operation()
        except Unavailable:
            sleep(0.1 * 2**attempt)
    return operation()
