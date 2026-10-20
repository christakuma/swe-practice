"""Counter-example: the page stops waiting for recommendations, and the call goes on."""

import asyncio

RECOMMENDATIONS_BUDGET = 0.3


async def load_dashboard(user_id, services):
    pending = asyncio.ensure_future(services.recommendations(user_id))
    profile, orders, notifications = await asyncio.gather(
        services.profile(user_id),
        services.orders(user_id),
        services.notifications(user_id),
    )
    done, _ = await asyncio.wait({pending}, timeout=RECOMMENDATIONS_BUDGET)
    recommendations = None
    if pending in done and pending.exception() is None:
        recommendations = pending.result()
    return {
        "profile": profile,
        "orders": orders,
        "notifications": notifications,
        "recommendations": recommendations,
    }
