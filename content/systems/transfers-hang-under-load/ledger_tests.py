"""The hidden tests for the lock-order fix.

Each test's docstring is the label a solver reads in the verdict, so they are
sentences about what `transfer` must do.

**The deadlock is caught without a deadlock.** `RecordingLock` notes, every
time a lock is taken, which locks the taking thread already held; those "held
A, then took B" pairs are the lock-order graph, and a cycle in it is a
deadlock waiting for the right timing. That makes the central check
deterministic and instant: the bug shows on two calls in one thread, so no
test here waits for threads to collide by luck.

The one test that does use threads asks the opposite question -- can two
transfers between unrelated accounts be inside `transfer` at the same time --
and it is decided by a barrier, so a correct answer passes as soon as both
threads arrive and a serialised one fails when the barrier times out.
"""

from __future__ import annotations

import random
import threading
import time

import pytest
from solution import InsufficientFunds, transfer

#: How long the parallelism test waits for the second thread. Long enough not
#: to fail a correct answer on a loaded machine; a serialised answer cannot
#: pass however long it is.
BARRIER_SECONDS = 5.0


class LockOrder:
    """Every "held A, then took B" pair seen, across all threads."""

    def __init__(self) -> None:
        self.edges: set[tuple[int, int]] = set()
        self._held = threading.local()

    def held(self) -> list[RecordingLock]:
        if not hasattr(self._held, "locks"):
            self._held.locks = []
        return self._held.locks

    def has_cycle(self) -> bool:
        graph: dict[int, set[int]] = {}
        for before, after in self.edges:
            graph.setdefault(before, set()).add(after)
        done: set[int] = set()
        path: set[int] = set()

        def visit(node: int) -> bool:
            if node in path:
                return True
            if node in done:
                return False
            path.add(node)
            found = any(visit(after) for after in graph.get(node, ()))
            path.discard(node)
            done.add(node)
            return found

        return any(visit(node) for node in list(graph))


class RecordingLock:
    """A `threading.Lock` that reports the order it is taken in."""

    def __init__(self, owner: int, order: LockOrder) -> None:
        self.owner = owner
        self._order = order
        self._lock = threading.Lock()

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        held = self._order.held()
        for other in held:
            self._order.edges.add((other.owner, self.owner))
        taken = self._lock.acquire(blocking, timeout)
        if taken:
            held.append(self)
        return taken

    def release(self) -> None:
        self._order.held().remove(self)
        self._lock.release()

    def locked(self) -> bool:
        return self._lock.locked()

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, *_: object) -> None:
        self.release()


class Account:
    """What the ledger hands `transfer`: an id, a balance and a lock."""

    def __init__(self, account_id: int, balance: int, order: LockOrder) -> None:
        self.id = account_id
        self.balance = balance
        self.lock = RecordingLock(account_id, order)


class GatedAccount(Account):
    """An account whose balance cannot be written until a partner arrives."""

    def __init__(
        self, account_id: int, balance: int, order: LockOrder, gate: threading.Barrier
    ) -> None:
        self._gate = gate
        self._balance = balance
        super().__init__(account_id, balance, order)

    @property
    def balance(self) -> int:
        return self._balance

    @balance.setter
    def balance(self, value: int) -> None:
        if hasattr(self, "_gate") and value != self._balance:
            self._gate.wait()
        self._balance = value


@pytest.fixture
def order() -> LockOrder:
    return LockOrder()


def test_moves_the_amount(order: LockOrder) -> None:
    """A transfer moves the amount from the source to the target."""
    source, target = Account(1, 100, order), Account(2, 5, order)
    transfer(source, target, 30)
    assert (source.balance, target.balance) == (70, 35)


def test_insufficient_funds_moves_nothing(order: LockOrder) -> None:
    """A transfer the source cannot cover raises InsufficientFunds and moves nothing."""
    source, target = Account(1, 10, order), Account(2, 5, order)
    with pytest.raises(InsufficientFunds):
        transfer(source, target, 30)
    assert (source.balance, target.balance) == (10, 5)


def test_a_refused_transfer_releases_both_locks(order: LockOrder) -> None:
    """A transfer refused for insufficient funds leaves both accounts unlocked."""
    source, target = Account(1, 10, order), Account(2, 5, order)
    with pytest.raises(InsufficientFunds):
        transfer(source, target, 30)
    assert not source.lock.locked()
    assert not target.lock.locked()


def test_a_completed_transfer_releases_both_locks(order: LockOrder) -> None:
    """A completed transfer leaves both accounts unlocked."""
    source, target = Account(1, 100, order), Account(2, 5, order)
    transfer(source, target, 30)
    assert not source.lock.locked()
    assert not target.lock.locked()


def test_the_same_account_is_refused(order: LockOrder) -> None:
    """A transfer from an account to itself raises ValueError and takes no lock."""
    account = Account(1, 100, order)
    with pytest.raises(ValueError, match="same account"):
        transfer(account, account, 30)
    assert not account.lock.locked()
    assert account.balance == 100


def test_both_directions_lock_in_the_same_order(order: LockOrder) -> None:
    """Two accounts are always locked in the same order, whichever way money moves."""
    low, high = Account(17, 100, order), Account(42, 100, order)
    transfer(low, high, 10)
    transfer(high, low, 10)
    assert not order.has_cycle(), f"lock order seen: {sorted(order.edges)}"


def test_no_lock_order_cycle_across_many_accounts(order: LockOrder) -> None:
    """Across many accounts and directions, the order locks are taken never cycles."""
    accounts = [Account(account_id, 1_000, order) for account_id in (5, 3, 9, 1, 7)]
    chooser = random.Random(311)
    for _ in range(200):
        source, target = chooser.sample(accounts, 2)
        transfer(source, target, 1)
    assert not order.has_cycle(), f"lock order seen: {sorted(order.edges)}"


def test_unrelated_transfers_do_not_wait_for_each_other(order: LockOrder) -> None:
    """Two transfers between unrelated accounts can run at the same time."""
    gate = threading.Barrier(2, timeout=BARRIER_SECONDS)
    pairs = [
        (GatedAccount(1, 100, order, gate), Account(2, 0, order)),
        (GatedAccount(3, 100, order, gate), Account(4, 0, order)),
    ]
    errors: list[BaseException] = []

    def run(source: Account, target: Account) -> None:
        try:
            transfer(source, target, 10)
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=run, args=pair, daemon=True) for pair in pairs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=BARRIER_SECONDS * 2)
    assert not errors, (
        "the two transfers never ran at the same time: one waited for the "
        "other to finish"
    )
    assert [target.balance for _, target in pairs] == [10, 10]


def test_many_threads_finish_and_conserve_money(order: LockOrder) -> None:
    """Eight threads moving money among six accounts all finish, and none is lost."""
    accounts = [Account(account_id, 10_000, order) for account_id in range(6)]
    plans = []
    for seed in range(8):
        chooser = random.Random(seed)
        plans.append([tuple(chooser.sample(accounts, 2)) for _ in range(300)])

    def run(plan: list[tuple[Account, Account]]) -> None:
        for source, target in plan:
            transfer(source, target, 1)

    threads = [
        threading.Thread(target=run, args=(plan,), daemon=True) for plan in plans
    ]
    for thread in threads:
        thread.start()
    # One deadline for all eight, not ten seconds each: a deadlocked answer
    # would otherwise hold the suite for eighty and be killed before it could
    # be told why.
    deadline = time.monotonic() + 10
    for thread in threads:
        thread.join(timeout=max(0.0, deadline - time.monotonic()))
    assert not any(thread.is_alive() for thread in threads), "transfers deadlocked"
    assert sum(account.balance for account in accounts) == 60_000
