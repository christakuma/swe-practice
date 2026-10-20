"""Counter-example: one lock for the whole ledger. No deadlock, and no parallelism."""

import threading

_LEDGER = threading.Lock()


class InsufficientFunds(Exception):
    pass


def transfer(source, target, amount):
    if source is target:
        raise ValueError("cannot transfer to the same account")
    with _LEDGER:
        if source.balance < amount:
            raise InsufficientFunds(source.id)
        source.balance -= amount
        target.balance += amount
