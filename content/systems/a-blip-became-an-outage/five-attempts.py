"""Counter-example: four retries, read as four attempts after the first."""


class Unavailable(Exception):
    """The database could not be reached. The call did not happen."""


ATTEMPTS = 5


def call_with_retries(operation, *, sleep, rng):
    for attempt in range(1, ATTEMPTS):
        try:
            return operation()
        except Unavailable:
            sleep(rng.uniform(0, 0.1 * 2**attempt))
    return operation()
