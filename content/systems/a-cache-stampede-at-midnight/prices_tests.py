"""The hidden tests for coalescing the price cache's misses.

**Fifty callers arrive at once, deterministically.** `asyncio` only switches
tasks at an `await`, so a test can start fifty `get`s, let the loop turn
until every one of them is parked, and only then let the database answer.
By that point every caller has missed the cache and had its chance to start
a load of its own, so the number of loads is the answer's behaviour rather
than an accident of scheduling.

`Database.load_price` waits at a gate the test opens. A test that needs two
loads to overlap opens each product's gate only when the other product's load
has started, so an answer that lets one load at a time through fails at
`GUARD_SECONDS` rather than by a timing measurement.
"""

from __future__ import annotations

import asyncio

import pytest
from solution import PriceCache

GUARD_SECONDS = 2.0
TURNS = 20


class Cache:
    """The shared cache: a dictionary, with `expire` standing in for a TTL."""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    async def get(self, key: str) -> int | None:
        return self.values.get(key)

    async def set(self, key: str, value: int, ttl: int) -> None:
        assert ttl > 0
        self.values[key] = value

    def expire(self, key: str) -> None:
        self.values.pop(key, None)


class Outage(Exception):
    pass


class Database:
    def __init__(self, prices: dict[str, int]) -> None:
        self.prices = dict(prices)
        self.loads: list[str] = []
        self.gates: dict[str, asyncio.Event] = {}
        self.down = False

    def gate(self, key: str) -> asyncio.Event:
        return self.gates.setdefault(key, asyncio.Event())

    async def load_price(self, key: str) -> int:
        self.loads.append(key)
        if key in self.gates:
            await self.gates[key].wait()
        if self.down:
            message = f"could not load {key}"
            raise Outage(message)
        return self.prices[key]


async def settle() -> None:
    """Turn the loop until every task that can run has reached its next wait."""
    for _ in range(TURNS):
        await asyncio.sleep(0)


def run(test: object) -> None:
    asyncio.run(asyncio.wait_for(test(), GUARD_SECONDS))  # type: ignore[operator]


def test_a_hit_does_not_load() -> None:
    """A price in the cache is returned without a load."""

    async def test() -> None:
        cache, db = Cache(), Database({"sku-1": 999})
        cache.values["sku-1"] = 999
        assert await PriceCache(cache, db).get("sku-1") == 999
        assert db.loads == []

    run(test)


def test_a_miss_loads_and_fills_the_cache() -> None:
    """A miss loads the price once and stores it."""

    async def test() -> None:
        cache, db = Cache(), Database({"sku-1": 999})
        prices = PriceCache(cache, db)
        assert await prices.get("sku-1") == 999
        assert await prices.get("sku-1") == 999
        assert db.loads == ["sku-1"]
        assert cache.values == {"sku-1": 999}

    run(test)


def test_fifty_misses_at_once_load_once() -> None:
    """Fifty callers that miss at the same moment share one load."""

    async def test() -> None:
        cache, db = Cache(), Database({"sku-1": 999})
        prices = PriceCache(cache, db)
        gate = db.gate("sku-1")
        callers = [asyncio.ensure_future(prices.get("sku-1")) for _ in range(50)]
        await settle()
        gate.set()
        assert await asyncio.gather(*callers) == [999] * 50
        assert db.loads == ["sku-1"]

    run(test)


def test_two_products_load_side_by_side() -> None:
    """A load of one product does not wait for a load of another."""

    async def test() -> None:
        cache, db = Cache(), Database({"sku-1": 999, "sku-2": 1499})
        prices = PriceCache(cache, db)
        db.gate("sku-1")
        db.gate("sku-2")
        first = asyncio.ensure_future(prices.get("sku-1"))
        second = asyncio.ensure_future(prices.get("sku-2"))
        await settle()
        # Both loads have to be under way before either is let through.
        assert sorted(db.loads) == ["sku-1", "sku-2"]
        db.gates["sku-1"].set()
        db.gates["sku-2"].set()
        assert await asyncio.gather(first, second) == [999, 1499]

    run(test)


def test_a_failed_load_fails_every_caller_waiting_on_it() -> None:
    """Ten callers waiting on one load that fails all see its error, after one load."""

    async def test() -> None:
        cache, db = Cache(), Database({"sku-1": 999})
        prices = PriceCache(cache, db)
        db.down = True
        gate = db.gate("sku-1")
        callers = [asyncio.ensure_future(prices.get("sku-1")) for _ in range(10)]
        await settle()
        gate.set()
        results = await asyncio.gather(*callers, return_exceptions=True)
        assert all(isinstance(result, Outage) for result in results), results
        assert db.loads == ["sku-1"]

    run(test)


def test_a_failure_is_not_remembered() -> None:
    """After a failed load, the next miss loads again, and gets the price."""

    async def test() -> None:
        cache, db = Cache(), Database({"sku-1": 999})
        prices = PriceCache(cache, db)
        db.down = True
        with pytest.raises(Outage):
            await prices.get("sku-1")
        db.down = False
        assert await prices.get("sku-1") == 999
        assert db.loads == ["sku-1", "sku-1"]

    run(test)


def test_a_later_miss_loads_the_new_price() -> None:
    """Once the cached price expires, the next miss loads the price as it is now."""

    async def test() -> None:
        cache, db = Cache(), Database({"sku-1": 999})
        prices = PriceCache(cache, db)
        assert await prices.get("sku-1") == 999
        cache.expire("sku-1")
        db.prices["sku-1"] = 899
        assert await prices.get("sku-1") == 899

    run(test)
