"""Counter-example: one query per line still, but run on a thread pool."""

from concurrent.futures import ThreadPoolExecutor


def render_order(order_id, db):
    order = db.get_order(order_id)
    items = db.get_line_items(order_id)
    with ThreadPoolExecutor(max_workers=10) as pool:
        products = list(pool.map(lambda item: db.get_product(item.product_id), items))
    lines = [
        (product.name, item.quantity, product.in_stock)
        for item, product in zip(items, products, strict=True)
    ]
    return {"order": order.id, "lines": lines}
