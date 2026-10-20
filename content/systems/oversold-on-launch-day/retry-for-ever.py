"""Counter-example: compare-and-set, retried until it wins."""


class SoldOut(Exception):
    pass


class Contended(Exception):
    pass


def reserve(store, sku, quantity):
    while True:
        item = store.get(sku)
        if item.stock < quantity:
            raise SoldOut(sku)
        left = item.stock - quantity
        if store.put_if_version(sku, left, item.version):
            return left
