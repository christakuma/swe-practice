"""Counter-example: coalesced, and a finished load is never forgotten."""

import asyncio

TTL_SECONDS = 24 * 60 * 60


class PriceCache:
    def __init__(self, cache, db):
        self.cache = cache
        self.db = db
        self.loading = {}

    async def get(self, product_id):
        price = await self.cache.get(product_id)
        if price is not None:
            return price
        if product_id not in self.loading:
            self.loading[product_id] = asyncio.ensure_future(self._load(product_id))
        return await self.loading[product_id]

    async def _load(self, product_id):
        price = await self.db.load_price(product_id)
        await self.cache.set(product_id, price, ttl=TTL_SECONDS)
        return price
