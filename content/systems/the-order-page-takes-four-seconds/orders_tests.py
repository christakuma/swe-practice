"""The hidden tests for batching the order page's product lookups.

`CountingDb` records every call, so a test can say how many round trips a
render made, which is the whole of the bug: each query is fast, and there were
252 of them. It hands out a fresh copy of a product on every read, the way a
database does, so an answer that keeps products between calls sees old stock
rather than the change.

**Each test uses product ids of its own** (1000s, 2000s, ...). An answer that
caches across calls is wrong for one reason, stale stock, and should fail for
that reason only; shared ids would let one test's cached products fail
another's for a reason that depended on the order the tests ran in.
"""

from __future__ import annotations

import dataclasses
import math

from solution import render_order


@dataclasses.dataclass
class Order:
    id: int


@dataclasses.dataclass
class LineItem:
    product_id: int
    quantity: int


@dataclasses.dataclass
class Product:
    id: int
    name: str
    in_stock: bool


class CountingDb:
    """The repository `render_order` is given, with every call recorded."""

    BATCH_LIMIT = 100

    def __init__(self, items: list[LineItem]) -> None:
        self.items = items
        self.products = {
            item.product_id: Product(
                item.product_id, f"product {item.product_id}", True
            )
            for item in items
        }
        self.calls: list[str] = []

    @property
    def queries(self) -> int:
        return len(self.calls)

    def get_order(self, order_id: int) -> Order:
        self.calls.append("order")
        return Order(order_id)

    def get_line_items(self, order_id: int) -> list[LineItem]:
        del order_id
        self.calls.append("line items")
        return [dataclasses.replace(item) for item in self.items]

    def get_product(self, product_id: int) -> Product:
        self.calls.append("product")
        return dataclasses.replace(self.products[product_id])

    def get_products(self, ids: list[int]) -> dict[int, Product]:
        ids = list(ids)
        if len(ids) > self.BATCH_LIMIT:
            message = f"get_products takes at most 100 ids, and was given {len(ids)}"
            raise ValueError(message)
        self.calls.append("products")
        return {
            product_id: dataclasses.replace(self.products[product_id])
            for product_id in ids
        }


def order_of(product_ids: list[int]) -> CountingDb:
    return CountingDb(
        [
            LineItem(product_id, quantity)
            for quantity, product_id in enumerate(product_ids, 1)
        ]
    )


def expected_lines(db: CountingDb) -> list[tuple[str, int, bool]]:
    return [
        (
            db.products[item.product_id].name,
            item.quantity,
            db.products[item.product_id].in_stock,
        )
        for item in db.items
    ]


def test_renders_every_line_in_order() -> None:
    """Every line is rendered, in the order of the line items."""
    db = order_of([1003, 1001, 1002])
    page = render_order(8812, db)
    assert page == {"order": 8812, "lines": expected_lines(db)}


def test_a_small_order_takes_three_queries() -> None:
    """A three-line order takes three queries: the order, its lines, its products."""
    db = order_of([2001, 2002, 2003])
    render_order(8812, db)
    assert db.queries <= 3, db.calls


def test_a_250_line_order_takes_five_queries() -> None:
    """A 250-line order takes five queries, asking for at most 100 products at once."""
    ids = list(range(3000, 3250))
    db = order_of(ids)
    page = render_order(8812, db)
    assert page["lines"] == expected_lines(db)
    assert db.queries <= 2 + math.ceil(len(ids) / 100), db.calls


def test_a_repeated_product_is_fetched_once() -> None:
    """An order of 150 lines naming 60 products takes three queries."""
    ids = [4000 + index % 60 for index in range(150)]
    db = order_of(ids)
    page = render_order(8812, db)
    assert page["lines"] == expected_lines(db)
    assert db.queries <= 3, db.calls


def test_an_order_with_no_lines_renders_empty() -> None:
    """An order with no lines renders with no lines."""
    db = order_of([])
    assert render_order(8812, db) == {"order": 8812, "lines": []}


def test_stock_is_read_fresh_on_every_call() -> None:
    """A product that goes out of stock shows as out of stock on the next render."""
    db = order_of([5001, 5002])
    render_order(8812, db)
    db.products[5002].in_stock = False
    page = render_order(8812, db)
    assert page["lines"] == expected_lines(db)
