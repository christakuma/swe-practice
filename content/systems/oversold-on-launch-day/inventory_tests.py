"""The hidden tests for reserving stock without overselling.

**The other replica is played by the store itself.** `Store.get` can run a
sale of its own after it has taken its snapshot and before it returns, which
is exactly the window two replicas race through: one has read the stock, and
the other writes before the first one does. Nothing here starts a thread, so
the race happens on every run rather than on the unlucky ones, and a lock
taken in this process -- the fix the ticket says was tried -- is visibly no
help, because the sale that slips in never goes through it.

`Store` refuses to be read more than `READ_LIMIT` times in one test, so an
answer that retries for ever fails a test rather than hanging the suite.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest
from solution import Contended, SoldOut, reserve

if TYPE_CHECKING:
    from collections.abc import Callable

READ_LIMIT = 50


@dataclasses.dataclass(frozen=True)
class Item:
    stock: int
    version: int


class Store:
    """A key-value store with a version per key and compare-and-set by version."""

    def __init__(self, stock: int) -> None:
        self._stock = stock
        self._version = 1
        self.reads = 0
        self.conditional_writes = 0
        self.after_read: list[Callable[[], None]] = []

    @property
    def stock(self) -> int:
        return self._stock

    def get(self, sku: str) -> Item:
        del sku
        self.reads += 1
        if self.reads > READ_LIMIT:
            message = f"read {self.reads} times for one reservation"
            raise RuntimeError(message)
        item = Item(self._stock, self._version)
        if self.after_read:
            self.after_read.pop(0)()
        return item

    def put(self, sku: str, stock: int) -> None:
        del sku
        self._stock = stock
        self._version += 1

    def put_if_version(self, sku: str, stock: int, version: int) -> bool:
        del sku
        self.conditional_writes += 1
        if version != self._version:
            return False
        self._stock = stock
        self._version += 1
        return True

    def sale_elsewhere(self, quantity: int) -> Callable[[], None]:
        """Another replica's whole reservation, landing between a read and its write."""

        def sell() -> None:
            self._stock -= quantity
            self._version += 1

        return sell


def test_a_reservation_takes_its_quantity() -> None:
    """Reserving 3 of 10 leaves 7, and returns what is left."""
    store = Store(10)
    assert reserve(store, "sneaker-41", 3) == 7
    assert store.stock == 7


def test_too_few_left_is_sold_out_and_writes_nothing() -> None:
    """Asking for 3 when 2 are left raises SoldOut and writes nothing."""
    store = Store(2)
    with pytest.raises(SoldOut):
        reserve(store, "sneaker-41", 3)
    assert store.stock == 2
    assert store.conditional_writes == 0


def test_a_sale_on_another_replica_is_not_overwritten() -> None:
    """Another replica sells 4 between the read and the write: 10 - 4 - 3 leaves 3."""
    store = Store(10)
    store.after_read.append(store.sale_elsewhere(4))
    assert reserve(store, "sneaker-41", 3) == 3
    assert store.stock == 3


def test_the_last_pair_is_sold_once() -> None:
    """One pair left, and another replica sells it first: this buyer gets SoldOut."""
    store = Store(1)
    store.after_read.append(store.sale_elsewhere(1))
    with pytest.raises(SoldOut):
        reserve(store, "sneaker-41", 1)
    assert store.stock == 0


def test_it_gives_up_after_five_attempts() -> None:
    """Five lost writes in a row raise Contended, after exactly five attempts."""
    store = Store(10)
    store.after_read.extend(store.sale_elsewhere(0) for _ in range(READ_LIMIT))
    with pytest.raises(Contended):
        reserve(store, "sneaker-41", 1)
    assert store.conditional_writes == 5
    assert store.stock == 10
