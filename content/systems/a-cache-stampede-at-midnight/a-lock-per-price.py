"""Counter-example: a lock per product, and the cache checked again inside it."""

import asyncio

TTL_SECONDS = 24 * 60 * 60


class PriceCache:
    def __init__(self, cache, db):
        self.cache = cache
        self.db = db
        self.locks = {}

    async def get(self, product_id):
        price = await self.cache.get(product_id)
        if price is not None:
            return price
        lock = self.locks.setdefault(product_id, asyncio.Lock())
        async with lock:
            price = await self.cache.get(product_id)
            if price is None:
                price = await self.db.load_price(product_id)
                await self.cache.set(product_id, price, ttl=TTL_SECONDS)
            return price
