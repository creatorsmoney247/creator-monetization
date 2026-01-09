from telegram import Update
from telegram.ext import ContextTypes


async def start_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🟢 [START.PY HANDLER HIT]")

    message = update.effective_message
    if not message:
        return

    await message.reply_text(
        "👋 **Welcome to Creator Monetization Bot**\n\n"
        "✨ *Unlock the hidden power of your social media presence!* ✨\n"
        "Grow your influence, master virality, and build a brand that sells.\n\n"
        "Creators don’t fail because they lack talent — they fail because they **undercharge**.\n\n"
        "This bot helps you:\n"
        "💰 Discover what brands SHOULD pay you\n"
        "📊 Know if you’re being undervalued\n"
        "🧠 Price yourself with confidence (without sounding greedy)\n\n"
        "⚠️ Most creators leave money on the table simply because they don’t know their real market value.\n\n"
        "———\n"
        "💰 Built for creators who want\n"
        "**money + long-term credibility**.\n\n"
        "📈 **Get your pricing insight in 10 seconds**\n\n"
        "Send your stats in this format:\n"
        "`followers  avg_views  engagement_rate`\n\n"
        "Example:\n"
        "`50k 12k 0.08`\n\n"
        "You’ll instantly see:\n"
        "• Recommended brand price range\n"
        "• Minimum acceptable rate (never go below this)\n"
        "• Where you sit in the creator market\n\n"
        "🔓 **PRO creators unlock:**\n"
        "• Brand deal reply scripts\n"
        "• Negotiation leverage\n"
        "• Monetization positioning tools and others\n\n"
        "✨ If you want to turn your reach into money, PRO shows you how.\n\n"
        "👉 **Send your stats now to begin**\n\n"
        "ℹ️ Need help? Type `/help` anytime.",
        parse_mode="Markdown",
    )
