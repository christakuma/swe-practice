"""Counter-example: the right order, released only on the way out that worked."""


class InsufficientFunds(Exception):
    pass


def transfer(source, target, amount):
    if source is target:
        raise ValueError("cannot transfer to the same account")
    first, second = sorted((source, target), key=lambda account: account.id)
    first.lock.acquire()
    second.lock.acquire()
    if source.balance < amount:
        raise InsufficientFunds(source.id)
    source.balance -= amount
    target.balance += amount
    second.lock.release()
    first.lock.release()
