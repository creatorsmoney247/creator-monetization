from bot.handlers.deal import deal_step_handler
from bot.handlers.pricing import pricing_calc


async def text_router(update, context):
    """
    Routes ALL plain text based on user state.
    """

    mode = context.user_data.get("mode")

    if mode == "deal":
        return await deal_step_handler(update, context)

    # Default: pricing
    return await pricing_calc(update, context)
