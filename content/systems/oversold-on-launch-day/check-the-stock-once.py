"""Counter-example: the stock is checked on the first read and not after a conflict."""


class SoldOut(Exception):
    pass


class Contended(Exception):
    pass


def reserve(store, sku, quantity):
    item = store.get(sku)
    if item.stock < quantity:
        raise SoldOut(sku)
    for _ in range(5):
        left = item.stock - quantity
        if store.put_if_version(sku, left, item.version):
            return left
        item = store.get(sku)
    raise Contended(sku)
