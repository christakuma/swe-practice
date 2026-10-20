"""Counter-example: one lock in front of every load, and the cache checked again."""

import asyncio

TTL_SECONDS = 24 * 60 * 60


class PriceCache:
    def __init__(self, cache, db):
        self.cache = cache
        self.db = db
        self.lock = asyncio.Lock()

    async def get(self, product_id):
        price = await self.cache.get(product_id)
        if price is not None:
            return price
        async with self.lock:
            price = await self.cache.get(product_id)
            if price is None:
                price = await self.db.load_price(product_id)
                await self.cache.set(product_id, price, ttl=TTL_SECONDS)
            return price
