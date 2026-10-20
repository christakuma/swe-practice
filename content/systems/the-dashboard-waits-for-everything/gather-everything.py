"""Counter-example: all four at once, and the page waits for the slowest."""

import asyncio

RECOMMENDATIONS_BUDGET = 0.3


async def load_dashboard(user_id, services):
    profile, orders, notifications, recommendations = await asyncio.gather(
        services.profile(user_id),
        services.orders(user_id),
        services.notifications(user_id),
        services.recommendations(user_id),
    )
    return {
        "profile": profile,
        "orders": orders,
        "notifications": notifications,
        "recommendations": recommendations,
    }
